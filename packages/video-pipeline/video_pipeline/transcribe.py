"""Transcribe audio chunks using Whisper API."""

import json
import logging
from pathlib import Path
from typing import List
from openai import OpenAI
from .config import get_config
from .errors import TranscribeError

logger = logging.getLogger(__name__)


def _mock_transcribe(chunk_info: dict) -> dict:
    """Produce deterministic placeholder segments for local E2E (MOCK_AI=true).

    Splits the chunk into ~5s windows with stub Chinese text so the downstream
    translate -> SRT -> render path has realistic, non-empty input. No network.
    """
    offset = float(chunk_info.get("start_offset_seconds", 0.0))
    duration = float(chunk_info.get("duration_seconds", 0.0)) or 5.0
    index = int(chunk_info.get("chunk_index", 0))

    segments = []
    window = 5.0
    n = max(1, int(duration // window) + (1 if duration % window else 0))
    for i in range(n):
        start = i * window
        end = min((i + 1) * window, duration)
        if start >= duration:
            break
        segments.append(
            {
                "start": offset + start,
                "end": offset + end,
                "text": f"模拟字幕 区块{index} 第{i + 1}句",
            }
        )
    return {"segments": segments}


def transcribe_chunk(chunk_path: Path, chunk_info: dict) -> dict:
    """
    Transcribe one audio chunk.

    Args:
        chunk_path: path to audio chunk
        chunk_info: metadata from chunk_audio

    Returns:
        Dict with 'segments' key containing list of segments with adjusted timestamps
    """
    cfg = get_config()

    if cfg.MOCK_AI:
        logger.warning("MOCK_AI enabled: stubbing transcription for chunk %s", chunk_info.get("chunk_index"))
        return _mock_transcribe(chunk_info)

    if not cfg.GROQ_API_KEY:
        raise TranscribeError("GROQ_API_KEY not configured")

    chunk_index = chunk_info.get("chunk_index")

    # Pre-flight diagnostics (worker logs only; never log the API key).
    chunk_path = Path(chunk_path)
    exists = chunk_path.exists()
    size = chunk_path.stat().st_size if exists else 0
    logger.info(
        "transcribe_chunk start: index=%s path=%s exists=%s size_bytes=%s model=%s",
        chunk_index,
        chunk_path,
        exists,
        size,
        cfg.GROQ_MODEL,
    )

    if not exists:
        logger.error(
            "transcribe_chunk: chunk file missing index=%s path=%s", chunk_index, chunk_path
        )
        raise TranscribeError(
            "Audio chunk file not found for transcription.",
            {
                "chunk_index": chunk_index,
                "chunk_path": str(chunk_path),
                "exists": False,
            },
        )
    if size == 0:
        logger.error(
            "transcribe_chunk: chunk file is empty index=%s path=%s", chunk_index, chunk_path
        )
        raise TranscribeError(
            "Audio chunk file is empty.",
            {"chunk_index": chunk_index, "chunk_path": str(chunk_path), "size_bytes": 0},
        )

    client = OpenAI(api_key=cfg.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

    try:
        with open(chunk_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=cfg.GROQ_MODEL,
                file=audio_file,
                language="zh",
                response_format="verbose_json",
            )
    except Exception as e:
        # Extract status / response detail when the OpenAI/Groq SDK exposes it,
        # without ever logging the API key.
        status_code = getattr(e, "status_code", None)
        response_text = None
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                response_text = resp.text[:500]
            except Exception:  # noqa: BLE001
                response_text = None
        logger.error(
            "transcribe_chunk: Groq Whisper API failed index=%s path=%s exists=%s "
            "size_bytes=%s model=%s status=%s error=%s response=%s",
            chunk_index,
            chunk_path,
            exists,
            size,
            cfg.GROQ_MODEL,
            status_code,
            str(e),
            response_text,
        )
        # User-facing message stays clean; details carry debug info (no secrets).
        raise TranscribeError(
            "Transcription failed while contacting the speech-to-text service.",
            {
                "chunk_index": chunk_index,
                "chunk_path": str(chunk_path),
                "exists": exists,
                "size_bytes": size,
                "model": cfg.GROQ_MODEL,
                "status_code": status_code,
            },
        )

    data = transcript.model_dump()
    offset = chunk_info["start_offset_seconds"]

    segments = data.get("segments", [])
    for seg in segments:
        seg["start"] += offset
        seg["end"] += offset

    return {"segments": segments}


def transcribe_all_chunks(chunks: List[dict], work_dir: Path) -> dict:
    """
    Transcribe all chunks and merge into single transcript.

    Args:
        chunks: list from chunk_audio
        work_dir: job work directory

    Returns:
        Dict with 'segments' containing all segments with unique IDs
    """
    transcript_dir = work_dir / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    all_segments = []
    global_id = 0

    for chunk in chunks:
        chunk_path = work_dir / chunk["path"]
        chunk_json = transcript_dir / f"chunk_{chunk['chunk_index']:03d}.json"

        logger.info(
            "transcribe_all_chunks: resolving chunk index=%s rel_path=%s -> %s (exists=%s)",
            chunk.get("chunk_index"),
            chunk.get("path"),
            chunk_path,
            chunk_path.exists(),
        )

        result = transcribe_chunk(chunk_path, chunk)

        with open(chunk_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        for seg in result["segments"]:
            seg["id"] = global_id
            all_segments.append(seg)
            global_id += 1

    merged = {"segments": all_segments}

    transcript_file = transcript_dir / "transcript.json"
    with open(transcript_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return merged
