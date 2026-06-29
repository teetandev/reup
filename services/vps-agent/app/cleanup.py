"""Job artifact cleanup for VPS Agent.

Periodically removes old job directories to prevent disk exhaustion.
Called from the heartbeat loop (see app/heartbeat.py).
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import Settings
from .logging_config import get_logger

logger = get_logger(__name__)


def cleanup_old_jobs(settings: Settings, retention_days: int = 7) -> None:
    """Delete job directories older than retention_days.

    Strategy:
    - DONE jobs: keep only output.mp4, delete intermediate files (audio, transcript, etc.)
    - FAILED/CANCELLED/incomplete jobs: delete entire directory

    Args:
        settings: Agent settings (provides WORK_DIR)
        retention_days: Keep jobs younger than this many days
    """
    jobs_dir = Path(settings.work_dir) / "jobs"
    if not jobs_dir.exists():
        logger.debug("Jobs directory does not exist, skipping cleanup: %s", jobs_dir)
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cleaned_count = 0
    kept_count = 0

    try:
        for job_dir in jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue

            try:
                # Check directory age via modification time
                mtime = datetime.fromtimestamp(job_dir.stat().st_mtime, tz=timezone.utc)
                if mtime > cutoff:
                    kept_count += 1
                    continue

                # Directory is old enough to clean
                output_path = job_dir / "output" / "output.mp4"

                if output_path.exists() and output_path.stat().st_size > 0:
                    # DONE job: keep only output.mp4, delete intermediate files
                    _cleanup_intermediates(job_dir)
                    cleaned_count += 1
                    logger.info("Cleaned intermediate files for DONE job: %s", job_dir.name)
                else:
                    # FAILED/CANCELLED/incomplete: delete entire directory
                    shutil.rmtree(job_dir, ignore_errors=True)
                    cleaned_count += 1
                    logger.info("Deleted old job directory: %s", job_dir.name)

            except Exception as exc:
                logger.warning("Failed to clean job directory %s: %s", job_dir.name, exc)
                continue

        if cleaned_count > 0:
            logger.info(
                "Cleanup complete: %d jobs cleaned, %d recent jobs kept",
                cleaned_count,
                kept_count,
            )

    except Exception as exc:
        logger.error("Job cleanup failed: %s", exc)


def _cleanup_intermediates(job_dir: Path) -> None:
    """Delete intermediate files, keep only output/output.mp4 and metadata.json.

    Removes:
    - input.mp4
    - audio/ directory
    - transcript/ directory
    - translation/ directory
    - subtitle/ directory
    - logs/ directory
    """
    keep_items = {"output", "metadata.json"}

    for item in job_dir.iterdir():
        if item.name in keep_items:
            continue

        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except Exception as exc:
            logger.debug("Failed to delete %s: %s", item, exc)
