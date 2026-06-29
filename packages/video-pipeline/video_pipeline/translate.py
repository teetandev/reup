"""Translate transcript using Gemini with checkpoint/retry logic."""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict
from google import genai
from google.genai import types
from google.genai.errors import APIError
from .config import get_config
from .errors import TranslateError

logger = logging.getLogger(__name__)


def _mock_translate(segments: List[dict], work_dir: Path) -> dict:
    """Stub Vietnamese translations for local E2E (MOCK_AI=true). No network."""
    translation_dir = work_dir / "translation"
    translation_dir.mkdir(parents=True, exist_ok=True)

    result_segments = []
    for seg in segments:
        seg_copy = seg.copy()
        original = seg.get("text", "")
        seg_copy["translation"] = f"[VI giả lập] {original}".strip()
        result_segments.append(seg_copy)

    result = {"segments": result_segments}
    with open(translation_dir / "translated.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def build_prompt() -> str:
    """Build translation prompt."""
    return (
        "You are a professional translator. Translate the following JSON array of subtitle segments from Chinese to Vietnamese. "
        "Follow these strict rules:\n"
        "1. Preserve the exact context and tone of the original text.\n"
        "2. Preserve the exact 'id' for each segment.\n"
        "3. Preserve the exact ordering of segments.\n"
        "4. NEVER summarize or omit any segments.\n"
        "5. NEVER add explanations or conversational text.\n"
        "6. Output MUST be a valid JSON array of objects, where each object contains ONLY two keys: 'id' and 'translation'.\n"
    )


def call_gemini_batch(client: genai.Client, model: str, batch: List[dict], retries: int = 3) -> List[dict]:
    """
    Call Gemini API for one batch with retry.

    Args:
        client: Gemini client
        model: model name
        batch: list of {id, text} dicts
        retries: number of retries

    Returns:
        List of {id, translation} dicts
    """
    prompt = build_prompt()
    input_json = json.dumps(batch, ensure_ascii=False, indent=2)
    contents = f"{prompt}\n\nInput JSON:\n{input_json}"

    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            if not response.text:
                raise TranslateError("Empty response from Gemini")

            result = json.loads(response.text)

            if not isinstance(result, list):
                raise TranslateError("Gemini response not a list")

            if len(result) != len(batch):
                raise TranslateError(f"Count mismatch: expected {len(batch)}, got {len(result)}")

            for item in result:
                if "id" not in item or "translation" not in item:
                    raise TranslateError(f"Missing keys in response item: {item}")

            return result

        except APIError as e:
            if e.code in [401, 403]:
                raise TranslateError("Gemini authentication failed", {"error": str(e)})
            if attempt == retries:
                raise TranslateError(f"Gemini API failed after {retries} retries", {"error": str(e)})
            time.sleep(2 ** attempt)
        except json.JSONDecodeError as e:
            if attempt == retries:
                raise TranslateError("Gemini returned invalid JSON", {"error": str(e)})
            time.sleep(2 ** attempt)
        except TranslateError:
            raise
        except Exception as e:
            if attempt == retries:
                raise TranslateError(f"Translation batch failed", {"error": str(e)})
            time.sleep(2 ** attempt)

    raise TranslateError("Translation failed after all retries")


def translate_transcript(transcript: dict, work_dir: Path) -> dict:
    """
    Translate full transcript with checkpointing.

    Args:
        transcript: dict with 'segments' list
        work_dir: job work directory

    Returns:
        Dict with 'segments' containing translated text
    """
    cfg = get_config()

    segments = transcript.get("segments", [])
    if not segments:
        raise TranslateError("No segments to translate")

    if cfg.MOCK_AI:
        logger.warning("MOCK_AI enabled: stubbing translation for %d segments", len(segments))
        return _mock_translate(segments, work_dir)

    if not cfg.GEMINI_API_KEY:
        raise TranslateError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=cfg.GEMINI_API_KEY)

    translation_dir = work_dir / "translation"
    translation_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_file = translation_dir / "checkpoint.json"
    output_file = translation_dir / "translated.json"

    translations_map = {}

    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
            translations_map = checkpoint.get("translations_map", {})

    batch_items = []
    for seg in segments:
        seg_id = str(seg["id"])
        if seg_id not in translations_map:
            batch_items.append({"id": seg["id"], "text": seg.get("text", "")})

    if not batch_items:
        result_segments = []
        for seg in segments:
            seg_copy = seg.copy()
            seg_copy["translation"] = translations_map[str(seg["id"])]
            result_segments.append(seg_copy)
        return {"segments": result_segments}

    batch_size = cfg.TRANSLATION_BATCH_SIZE
    batches = [batch_items[i:i + batch_size] for i in range(0, len(batch_items), batch_size)]

    for i, batch in enumerate(batches):
        batch_translations = call_gemini_batch(client, cfg.GEMINI_MODEL, batch)

        for trans in batch_translations:
            translations_map[str(trans["id"])] = trans["translation"]

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump({"translations_map": translations_map}, f, ensure_ascii=False, indent=2)

        if i < len(batches) - 1:
            time.sleep(5)

    result_segments = []
    for seg in segments:
        seg_copy = seg.copy()
        seg_copy["translation"] = translations_map.get(str(seg["id"]), "")
        result_segments.append(seg_copy)

    result = {"segments": result_segments}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result
