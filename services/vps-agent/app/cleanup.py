"""Job artifact cleanup for the VPS Agent — prevents disk exhaustion.

Three complementary mechanisms:

1. ``cleanup_intermediates_after_done(job_dir)`` — called by the pipeline runner
   immediately after a job reaches DONE. Removes every intermediate artifact
   (input.mp4, audio/, transcript/, translation/, subtitle/, metadata.json) and
   keeps only ``output/output.mp4`` so the user can still download it.

2. ``cleanup_after_download(job_dir)`` — scheduled via FastAPI ``BackgroundTasks``
   from the download endpoint. Runs *after* the file response has been streamed,
   then deletes the entire job folder.

3. ``cleanup_old_jobs(settings, current_job_id=...)`` — a TTL sweep run on startup
   and periodically from the heartbeat loop. Removes whole job folders whose
   ``output/output.mp4`` is older than ``OUTPUT_TTL_HOURS``. Never touches the
   job currently running.

Safety: every deletion goes through :func:`safe_delete_path`, which refuses to
remove anything that is not strictly inside ``WORK_DIR``.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .logging_config import get_logger

logger = get_logger(__name__)


# Items inside a job folder that are pure intermediates (safe to delete on DONE).
_INTERMEDIATE_ITEMS = (
    "input.mp4",
    "audio",
    "transcript",
    "translation",
    "subtitle",
    "metadata.json",
    "logs",
)
# What we keep after DONE so the user can still download.
_KEEP_AFTER_DONE = {"output"}


def _jobs_root(settings: Settings) -> Path:
    return Path(settings.work_dir).resolve() / "jobs"


def safe_delete_path(path: Path, work_dir: Path) -> bool:
    """Delete ``path`` only if it is strictly inside ``work_dir``.

    Returns True if something was deleted, False otherwise. Never raises — all
    errors are logged. This is the single choke point that prevents an accidental
    ``rmtree`` outside the agent's working directory.
    """
    try:
        path = Path(path).resolve()
        work_dir = Path(work_dir).resolve()
    except Exception as exc:  # noqa: BLE001
        logger.warning("safe_delete_path: failed to resolve paths: %s", exc)
        return False

    # Must be strictly under work_dir (and not work_dir itself).
    if path == work_dir or work_dir not in path.parents:
        logger.warning(
            "safe_delete_path: refusing to delete path outside WORK_DIR: path=%s work_dir=%s",
            path,
            work_dir,
        )
        return False

    if not path.exists():
        return False

    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("safe_delete_path: failed to delete %s: %s", path, exc)
        return False


def cleanup_intermediates_after_done(settings: Settings, job_id: str) -> None:
    """Delete intermediates for a freshly DONE job, keeping ``output/output.mp4``.

    Called from the pipeline runner right after a job reaches DONE.
    """
    work_dir = Path(settings.work_dir).resolve()
    job_dir = _jobs_root(settings) / job_id

    if not job_dir.exists():
        return

    logger.info("cleanup_intermediates_started job_id=%s dir=%s", job_id, job_dir)
    removed: list[str] = []
    for name in _INTERMEDIATE_ITEMS:
        if name in _KEEP_AFTER_DONE:
            continue
        target = job_dir / name
        if target.exists() and safe_delete_path(target, work_dir):
            removed.append(name)

    logger.info(
        "cleanup_intermediates_done job_id=%s removed=%s kept=output/output.mp4",
        job_id,
        removed,
    )


def cleanup_after_download(settings: Settings, job_id: str) -> None:
    """Delete the entire job folder after the output has been downloaded.

    Intended to run as a FastAPI BackgroundTask, i.e. *after* FileResponse has
    finished reading and streaming the file to the client.
    """
    work_dir = Path(settings.work_dir).resolve()
    job_dir = _jobs_root(settings) / job_id

    logger.info("cleanup_after_download_scheduled job_id=%s dir=%s", job_id, job_dir)
    deleted = safe_delete_path(job_dir, work_dir)
    logger.info("cleanup_after_download_done job_id=%s deleted=%s", job_id, deleted)


def cleanup_old_jobs(
    settings: Settings,
    current_job_id: str | None = None,
    ttl_hours: int | None = None,
) -> None:
    """TTL sweep: remove whole job folders whose output is older than the TTL.

    Args:
        settings: agent settings (provides WORK_DIR + OUTPUT_TTL_HOURS).
        current_job_id: the job currently running on this node — never deleted.
        ttl_hours: override the configured TTL (mostly for tests).

    Rules:
    - Only paths strictly under WORK_DIR are ever removed (via safe_delete_path).
    - The currently running job (``current_job_id``) is always skipped.
    - A job folder is removed only if ``output/output.mp4`` exists and its mtime
      is older than the TTL. Folders without a finished output are left for the
      job to finish (the pipeline cleans its own intermediates on DONE).
    """
    ttl = settings.output_ttl_hours if ttl_hours is None else ttl_hours
    if ttl <= 0:
        logger.debug("ttl_cleanup disabled (OUTPUT_TTL_HOURS=%s)", ttl)
        return

    work_dir = Path(settings.work_dir).resolve()
    jobs_dir = _jobs_root(settings)
    if not jobs_dir.exists():
        return

    cutoff_ts = datetime.now(timezone.utc).timestamp() - (ttl * 3600)
    removed = 0

    for job_dir in jobs_dir.iterdir():
        if not job_dir.is_dir():
            continue

        job_id = job_dir.name
        if current_job_id and job_id == current_job_id:
            logger.info("ttl_cleanup_skipped_running_job job_id=%s", job_id)
            continue

        output_path = job_dir / "output" / "output.mp4"
        if not output_path.exists():
            # Not finished (or no output) — leave it alone.
            continue

        try:
            mtime = output_path.stat().st_mtime
        except OSError:
            continue

        if mtime >= cutoff_ts:
            continue  # output still within TTL

        if safe_delete_path(job_dir, work_dir):
            removed += 1
            age_hours = (datetime.now(timezone.utc).timestamp() - mtime) / 3600
            logger.info(
                "ttl_cleanup_removed job_id=%s age_hours=%.1f ttl_hours=%s",
                job_id,
                age_hours,
                ttl,
            )

    if removed:
        logger.info("ttl_cleanup complete: removed=%d ttl_hours=%s", removed, ttl)
