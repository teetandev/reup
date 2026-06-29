"""Render hardsub video with low-resource FFmpeg settings."""

import subprocess
from pathlib import Path
from .config import get_config
from .errors import RenderError


def render_hardsub(video_path: Path, srt_path: Path, output_path: Path) -> Path:
    """
    Burn subtitles into video using FFmpeg.

    Args:
        video_path: input video
        srt_path: SRT subtitle file
        output_path: output video path

    Returns:
        Path to rendered video
    """
    cfg = get_config()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate subtitle path contains only safe characters
    srt_str = str(srt_path)
    if any(c in srt_str for c in ["'", '"', ';', '`', '$', '|', '&']):
        raise RenderError("Subtitle path contains unsafe characters", {"path": srt_str})

    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        cfg.FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        "-vf", f"subtitles={srt_escaped}:force_style='FontName=Arial,FontSize=22,Outline=2,Shadow=1,MarginV=30'",
        "-c:v", "libx264",
        "-preset", cfg.FFMPEG_PRESET,
        "-crf", str(cfg.FFMPEG_CRF),
        "-threads", str(cfg.FFMPEG_THREADS),
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RenderError("ffmpeg render failed", {"stderr": e.stderr[-1000:]})

    if not output_path.exists():
        raise RenderError("Output video not created")

    if output_path.stat().st_size == 0:
        raise RenderError("Output video is empty")

    return output_path
