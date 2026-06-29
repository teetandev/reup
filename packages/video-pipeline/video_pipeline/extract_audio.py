"""Extract audio from video."""

import subprocess
from pathlib import Path
from .config import get_config
from .errors import ExtractAudioError


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """
    Extract mono 16kHz audio from video to MP3.

    Args:
        video_path: input video
        output_path: output MP3 file

    Returns:
        Path to created MP3
    """
    cfg = get_config()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        cfg.FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "64k",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise ExtractAudioError("ffmpeg extraction failed", {"stderr": e.stderr[-500:]})

    if not output_path.exists():
        raise ExtractAudioError("Audio file not created")

    return output_path
