"""Run the video pipeline for one job and report progress (Phase 10).

This wires ``packages/video-pipeline`` into the VPS agent. The pipeline itself is
synchronous and CPU/IO heavy (ffmpeg + remote transcription/translation), so it runs
in a dedicated background **thread** — the asyncio event loop stays free to serve
``GET /jobs/{job_id}/status`` polls and ``/health`` while the job runs.

Responsibilities:
- Map pipeline progress percentages to canonical job statuses.
- Push status/progress to the Control API on every step (``POST /jobs/{id}/agent-status``).
- Persist the latest state locally (:mod:`app.job_runtime`) for status polls.
- Translate :class:`PipelineError` into a FAILED status with the right error code.
- Always release the node's single-job slot on DONE/FAILED/CANCELLED.

Secrets safety: the node token is sent only as an ``Authorization`` header and is never
logged. GROQ/GEMINI keys live in the pipeline's own config and are never touched here.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import httpx

from .config import Settings
from .job_runtime import get_job_registry
from .logging_config import get_logger
from .state import get_node_state

logger = get_logger(__name__)


class _PipelineCancelled(Exception):
    """Raised inside the progress callback when a cancel was requested."""


# --- progress -> job status mapping -------------------------------------------------
#
# packages/video-pipeline reports progress at fixed checkpoints, calling the callback
# *before* each step. We translate the percentage into the canonical job status enum.
# See docs/specs/PIPELINE_SPEC.md "Progress Mapping".

def map_progress_to_status(percent: float) -> str:
    """Map a pipeline progress percentage to a canonical job status."""
    if percent >= 100:
        return "DONE"
    if percent >= 70:
        return "RENDERING"
    if percent >= 65:
        return "GENERATING_SRT"
    if percent >= 45:
        return "TRANSLATING"
    if percent >= 15:
        return "TRANSCRIBING"
    if percent >= 10:
        return "CHUNKING_AUDIO"
    # 0-10%: validate + extract audio (no VALIDATING status exists in the enum).
    return "EXTRACTING_AUDIO"


def _ensure_pipeline_importable(settings: Settings) -> None:
    """Make ``video_pipeline`` importable in the monorepo layout.

    Production installs it as a package (``pip install -e packages/video-pipeline``),
    but in the dev tree we add it to ``sys.path`` so the agent runs without a build
    step. ``VIDEO_PIPELINE_PATH`` overrides the auto-detected location.
    """
    override = os.environ.get("VIDEO_PIPELINE_PATH")
    candidates = []
    if override:
        candidates.append(Path(override))
    # services/vps-agent/app/pipeline_runner.py -> repo root is parents[3]
    repo_root = Path(__file__).resolve().parents[3]
    candidates.append(repo_root / "packages" / "video-pipeline")

    for candidate in candidates:
        if (candidate / "video_pipeline" / "__init__.py").exists():
            path_str = str(candidate)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
            return
    # Not found on disk: leave sys.path alone and let the import below decide
    # (it may still be installed as a site-package).


def _notify_control(settings: Settings, job_id: str, **fields: object) -> None:
    """Best-effort status callback to the Control API. Never raises.

    Mirrors :func:`app.upload_service.notify_control_status` but synchronous, since the
    pipeline runs in a plain thread. Drops ``None`` fields. The node token is sent as a
    Bearer header and is never logged.
    """
    if not settings.control_api_url or not settings.node_token:
        # No control plane wired (local dev) — keep running, just don't report.
        logger.debug("Skipping status callback for job %s (control plane not configured)", job_id)
        return

    url = f"{settings.control_api_url.rstrip('/')}/jobs/{job_id}/agent-status"
    headers = {
        "Authorization": f"Bearer {settings.node_token}",
        "Content-Type": "application/json",
    }
    payload = {k: v for k, v in fields.items() if v is not None}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            logger.warning(
                "agent-status callback rejected: job=%s status=%s http=%s",
                job_id,
                fields.get("status"),
                resp.status_code,
            )
    except Exception as exc:  # noqa: BLE001 - callback must never break the pipeline
        logger.warning("agent-status callback failed: job=%s err=%s", job_id, exc)


def _release_local_slot(job_id: str) -> None:
    """Release this node's single-job slot, tolerating an already-released slot."""
    try:
        get_node_state().release_job(job_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Local slot release for job %s skipped: %s", job_id, exc)


def run_job_pipeline(job_id: str, settings: Settings) -> None:
    """Execute the full pipeline for ``job_id`` (blocking; call in a thread).

    On completion the local job record reflects the terminal status, the Control API
    has been notified, and the node's job slot has been released.
    """
    registry = get_job_registry()
    job_dir = Path(settings.work_dir) / "jobs" / job_id
    input_path = job_dir / "input.mp4"

    if not input_path.exists():
        logger.error("Cannot start pipeline: missing input for job %s", job_id)
        registry.update(
            job_id,
            status="FAILED",
            error_code="INPUT_NOT_FOUND",
            error_message="Input video not found for this job.",
        )
        _notify_control(
            settings,
            job_id,
            status="FAILED",
            error_code="INPUT_NOT_FOUND",
            error_message="Input video not found for this job.",
            message="Pipeline could not start: input missing.",
        )
        _release_local_slot(job_id)
        return

    _ensure_pipeline_importable(settings)
    try:
        from video_pipeline import run_pipeline
        from video_pipeline.errors import PipelineError
    except Exception as exc:  # noqa: BLE001 - import/config failure
        logger.exception("video_pipeline import failed for job %s", job_id)
        registry.update(
            job_id,
            status="FAILED",
            error_code="CONFIG_ERROR",
            error_message="Video pipeline is not available on this node.",
        )
        _notify_control(
            settings,
            job_id,
            status="FAILED",
            error_code="CONFIG_ERROR",
            error_message="Video pipeline is not available on this node.",
            message="Pipeline dependency import failed.",
        )
        _release_local_slot(job_id)
        return

    def progress_callback(percent: int, message: str) -> None:
        # Cooperative cancellation: checked at each pipeline step boundary.
        if registry.is_cancel_requested(job_id):
            raise _PipelineCancelled()

        status = map_progress_to_status(percent)
        if status == "DONE":
            # Final DONE is emitted once after the pipeline fully returns, below.
            return
        registry.update(job_id, status=status, progress_percent=percent, current_step=status)
        logger.info("job=%s progress=%s%% step=%s", job_id, percent, status)
        _notify_control(
            settings,
            job_id,
            status=status,
            current_step=status,
            progress_percent=float(percent),
            message=message,
        )

    try:
        run_pipeline(input_path, job_dir, progress_callback)
    except _PipelineCancelled:
        logger.info("Pipeline cancelled for job %s", job_id)
        registry.update(job_id, status="CANCELLED", current_step="CANCELLED")
        _notify_control(
            settings,
            job_id,
            status="CANCELLED",
            message="Job cancelled during processing.",
        )
        _release_local_slot(job_id)
        return
    except PipelineError as exc:
        # Structured pipeline failure: code is one of the ERROR_MODEL pipeline codes.
        rec = registry.get(job_id)
        step = rec.current_step if rec else None
        logger.error("Pipeline failed for job %s: code=%s msg=%s", job_id, exc.code, exc.message)
        registry.update(
            job_id,
            status="FAILED",
            error_code=exc.code,
            error_message=exc.message,
        )
        _notify_control(
            settings,
            job_id,
            status="FAILED",
            current_step=step,
            error_code=exc.code,
            error_message=exc.message,
            message=f"Pipeline failed at step {step or 'unknown'}.",
        )
        _release_local_slot(job_id)
        return
    except Exception as exc:  # noqa: BLE001 - unexpected crash
        logger.exception("Unexpected pipeline error for job %s", job_id)
        registry.update(
            job_id,
            status="FAILED",
            error_code="INTERNAL_ERROR",
            error_message="Pipeline failed unexpectedly.",
        )
        _notify_control(
            settings,
            job_id,
            status="FAILED",
            error_code="INTERNAL_ERROR",
            error_message="Pipeline failed unexpectedly.",
            message="Unexpected pipeline error.",
        )
        _release_local_slot(job_id)
        return

    # Success: verify output then mark DONE.
    output_path = job_dir / "output" / "output.mp4"
    if not output_path.exists():
        logger.error("Pipeline finished but output missing for job %s", job_id)
        registry.update(
            job_id,
            status="FAILED",
            error_code="OUTPUT_VERIFY_FAILED",
            error_message="Render completed but output file is missing.",
        )
        _notify_control(
            settings,
            job_id,
            status="FAILED",
            error_code="OUTPUT_VERIFY_FAILED",
            error_message="Render completed but output file is missing.",
            message="Output verification failed.",
        )
        _release_local_slot(job_id)
        return

    logger.info("Pipeline DONE for job %s -> %s", job_id, output_path)
    registry.update(job_id, status="DONE", progress_percent=100.0, current_step="DONE")
    _notify_control(
        settings,
        job_id,
        status="DONE",
        current_step="DONE",
        progress_percent=100.0,
        message="Job completed successfully.",
    )
    _release_local_slot(job_id)


def start_pipeline_thread(job_id: str, settings: Settings) -> None:
    """Spawn the pipeline worker for ``job_id`` in a daemon thread."""
    thread = threading.Thread(
        target=run_job_pipeline,
        args=(job_id, settings),
        name=f"pipeline-{job_id}",
        daemon=True,
    )
    thread.start()
