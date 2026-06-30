"""Chunk audio for transcription API limits."""

import subprocess
from pathlib import Path
from typing import List
from .config import get_config
from .errors import ChunkAudioError


def chunk_audio(audio_path: Path, output_dir: Path, duration: float) -> List[dict]:
    """
    Split audio into chunks.

    Args:
        audio_path: input MP3
        output_dir: directory for chunks
        duration: total audio duration in seconds

    Returns:
        List of chunk info dicts with keys:
            chunk_index: int
            start_offset_seconds: float
            duration_seconds: float
            path: str (relative to output_dir)
    """
    cfg = get_config()
    output_dir.mkdir(parents=True, exist_ok=True)

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

        chunks.append({
            "chunk_index": index,
            "start_offset_seconds": start,
            "duration_seconds": chunk_dur,
            "path": str(chunk_file.relative_to(output_dir.parent.parent))
        })

        start += chunk_dur
        index += 1

    return chunks
