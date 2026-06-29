"""Video validation using ffprobe."""

import json
import subprocess
from pathlib import Path
from .config import get_config
from .errors import ProbeError


def probe_video(video_path: Path) -> dict:
    """
    Validate video with ffprobe.

    Returns dict with:
        duration: float (seconds)
        has_audio: bool
        width: int
        height: int
        format: str
    """
    cfg = get_config()

    if not video_path.exists():
        raise ProbeError(f"Video file not found: {video_path}")

    cmd = [
        cfg.FFPROBE_BIN,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise ProbeError("ffprobe command failed", {"stderr": e.stderr})
    except json.JSONDecodeError as e:
        raise ProbeError("ffprobe output invalid JSON", {"error": str(e)})

    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))

    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]

    if not audio_streams:
        raise ProbeError("No audio stream found in video")

    width = 0
    height = 0
    if video_streams:
        width = video_streams[0].get("width", 0)
        height = video_streams[0].get("height", 0)

    return {
        "duration": duration,
        "has_audio": len(audio_streams) > 0,
        "width": width,
        "height": height,
        "format": fmt.get("format_name", "unknown")
    }
