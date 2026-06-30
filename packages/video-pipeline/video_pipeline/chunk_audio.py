"""Chunk audio for transcription API limits."""

import subprocess
from pathlib import Path
from typing import List
from .config import get_config
from .errors import ChunkAudioError


def chunk_audio(
    audio_path: Path,
    output_dir: Path,
    duration: float,
    work_dir: Path | None = None,
) -> List[dict]:
    """
    Split audio into chunks.

    Args:
        audio_path: input MP3
        output_dir: directory for chunks (typically ``work_dir/audio/chunks``)
        duration: total audio duration in seconds
        work_dir: the job working directory. Chunk ``path`` values are returned
            relative to this directory so that ``transcribe_all_chunks`` can
            reconstruct the absolute path with ``work_dir / chunk["path"]``.
            If omitted, it is inferred as ``output_dir.parent.parent`` (i.e.
            ``work_dir/audio/chunks`` -> ``work_dir``).

    Returns:
        List of chunk info dicts with keys:
            chunk_index: int
            start_offset_seconds: float
            duration_seconds: float
            path: str (relative to ``work_dir``, e.g. ``audio/chunks/chunk_000.mp3``)
    """
    cfg = get_config()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the directory that chunk paths should be expressed relative to.
    # transcribe_all_chunks() does `work_dir / chunk["path"]`, so paths MUST be
    # relative to the job work_dir (e.g. "audio/chunks/chunk_000.mp3"), never to
    # the chunks directory itself.
    if work_dir is not None:
        rel_base = Path(work_dir).resolve()
    else:
        rel_base = output_dir.resolve().parent.parent

    chunk_duration = cfg.MAX_CHUNK_DURATION_SEC
    chunks = []

    start = 0.0
    index = 0

    while start < duration:
        chunk_dur = min(chunk_duration, duration - start)
        chunk_file = output_dir / f"chunk_{index:03d}.mp3"

        cmd = [
            cfg.FFMPEG_BIN,
            "-y",
            "-i", str(audio_path),
            "-ss", str(start),
            "-t", str(chunk_dur),
            "-c", "copy",
            str(chunk_file)
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ChunkAudioError(f"Failed to create chunk {index}", {"stderr": e.stderr[-500:]})

        if not chunk_file.exists():
            raise ChunkAudioError(f"Chunk file not created: {chunk_file}")

        # Express path relative to the job work_dir so transcribe can rebuild it.
        try:
            rel_path = chunk_file.resolve().relative_to(rel_base)
        except ValueError:
            # Fallback: if the chunk somehow isn't under rel_base, store a path
            # relative to work_dir best-effort using the known layout.
            rel_path = Path("audio") / "chunks" / chunk_file.name

        chunks.append({
            "chunk_index": index,
            "start_offset_seconds": start,
            "duration_seconds": chunk_dur,
            "path": str(rel_path)
        })

        start += chunk_dur
        index += 1

    return chunks
