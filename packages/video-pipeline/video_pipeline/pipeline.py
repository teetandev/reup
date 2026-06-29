"""Main pipeline orchestration."""

import json
import os
from pathlib import Path
from typing import Optional, Callable
from .probe import probe_video
from .extract_audio import extract_audio
from .chunk_audio import chunk_audio
from .transcribe import transcribe_all_chunks
from .translate import translate_transcript
from .subtitle import generate_srt
from .render import render_hardsub
from .progress import ProgressCallback, report_progress
from .errors import PipelineError


def run_pipeline(
    video_path: Path,
    work_dir: Path,
    progress_callback: ProgressCallback = None
) -> dict:
    """
    Run complete video pipeline.

    Args:
        video_path: input video file
        work_dir: job working directory for artifacts
        progress_callback: optional callback(percent: int, message: str)

    Returns:
        Dict with keys:
            output_video: Path
            metadata: dict
            artifacts: dict of paths

    Raises:
        PipelineError subclasses on failure
    """
    # Validate paths stay within expected boundaries
    try:
        video_path = video_path.resolve()
        work_dir = work_dir.resolve()

        # Ensure work_dir is under expected root (if WORK_DIR env var exists)
        work_root = os.environ.get("WORK_DIR")
        if work_root:
            work_root_resolved = Path(work_root).resolve()
            if not str(work_dir).startswith(str(work_root_resolved)):
                raise PipelineError(
                    "INVALID_PATH",
                    f"work_dir must be under {work_root}",
                    {"work_dir": str(work_dir)}
                )

        # Ensure video_path is inside work_dir
        if not str(video_path).startswith(str(work_dir)):
            raise PipelineError(
                "INVALID_PATH",
                "video_path must be inside work_dir",
                {"video_path": str(video_path), "work_dir": str(work_dir)}
            )
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError("INVALID_PATH", "Path validation failed") from exc

    work_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {}

    report_progress(progress_callback, 0, "Validating input video")
    metadata = probe_video(video_path)
    artifacts["metadata"] = metadata

    metadata_file = work_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    report_progress(progress_callback, 5, "Extracting audio")
    audio_dir = work_dir / "audio"
    audio_path = audio_dir / "full_audio.mp3"
    extract_audio(video_path, audio_path)
    artifacts["audio"] = str(audio_path)

    report_progress(progress_callback, 10, "Chunking audio")
    chunks_dir = audio_dir / "chunks"
    chunks = chunk_audio(audio_path, chunks_dir, metadata["duration"])
    artifacts["chunks"] = chunks

    report_progress(progress_callback, 15, "Transcribing audio")
    transcript = transcribe_all_chunks(chunks, work_dir)
    artifacts["transcript"] = str(work_dir / "transcript" / "transcript.json")

    report_progress(progress_callback, 45, "Translating to Vietnamese")
    translated = translate_transcript(transcript, work_dir)
    artifacts["translated"] = str(work_dir / "translation" / "translated.json")

    report_progress(progress_callback, 65, "Generating subtitles")
    subtitle_dir = work_dir / "subtitle"
    srt_path = subtitle_dir / "subtitle.srt"
    generate_srt(translated, srt_path)
    artifacts["srt"] = str(srt_path)

    report_progress(progress_callback, 70, "Rendering hardsub")
    output_dir = work_dir / "output"
    output_path = output_dir / "output.mp4"
    render_hardsub(video_path, srt_path, output_path)
    artifacts["output"] = str(output_path)

    report_progress(progress_callback, 100, "Pipeline complete")

    return {
        "output_video": output_path,
        "metadata": metadata,
        "artifacts": artifacts
    }
