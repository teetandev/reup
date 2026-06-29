"""Generate SRT subtitle file."""

from pathlib import Path
from .errors import SRTError


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(translated: dict, output_path: Path) -> Path:
    """
    Generate SRT file from translated segments.

    Args:
        translated: dict with 'segments' containing start, end, translation
        output_path: output .srt file path

    Returns:
        Path to created SRT file
    """
    segments = translated.get("segments", [])

    if not segments:
        raise SRTError("No segments to generate SRT")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for idx, seg in enumerate(segments, start=1):
            translation = seg.get("translation", "").strip()

            if not translation:
                continue

            start = seg.get("start", 0)
            end = seg.get("end", start)

            f.write(f"{idx}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            f.write(f"{translation}\n")
            f.write("\n")

    if not output_path.exists():
        raise SRTError("SRT file not created")

    return output_path
