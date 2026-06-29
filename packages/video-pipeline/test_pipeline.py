"""Smoke test for video pipeline."""

import sys
from pathlib import Path
from video_pipeline import run_pipeline


def progress_callback(percent: int, message: str):
    """Print progress updates."""
    print(f"[{percent:3d}%] {message}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <video_file>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    work_dir = Path("./test_output")

    print(f"Running pipeline on: {video_path}")
    print(f"Work directory: {work_dir}")
    print()

    try:
        result = run_pipeline(video_path, work_dir, progress_callback)

        print()
        print("Pipeline completed successfully!")
        print(f"Output video: {result['output_video']}")
        print(f"Duration: {result['metadata']['duration']:.2f}s")
        print(f"Resolution: {result['metadata']['width']}x{result['metadata']['height']}")

    except Exception as e:
        print(f"\nError: {e}")
        if hasattr(e, "details"):
            print(f"Details: {e.details}")
        sys.exit(1)


if __name__ == "__main__":
    main()
