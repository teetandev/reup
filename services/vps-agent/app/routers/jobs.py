"""Job processing router for the VPS agent (Phase 10).

Endpoints that drive a single job through the video pipeline on this node:

- ``POST /jobs/{job_id}/start``     start processing the already-uploaded input
- ``GET  /jobs/{job_id}/status``    poll local status/progress/current_step
- ``GET  /jobs/{job_id}/download``  download the rendered MP4 (only when DONE)
- ``POST /jobs/{job_id}/cancel``    best-effort cooperative cancel

The pipeline itself runs in a background thread (see :mod:`app.pipeline_runner`).
``start`` / ``cancel`` mutate state and require a Bearer token (the job's upload token,
validated with the Control API, or this node's own token). ``status`` / ``download`` are
read-only and rely on the unguessable job UUID as a capability (see Security notes).
"""

from __future__ import annotations

import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse, JSONResponse

from ..config import Settings, get_settings
from ..errors import AgentError
from ..job_runtime import get_job_registry
from ..logging_config import get_logger
from ..pipeline_runner import start_pipeline_thread
from ..state import NodeState, get_node_state
from ..upload_service import notify_control_status, validate_upload_token

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger(__name__)

# Statuses for which the pipeline is still running and must not be re-started.
_ACTIVE_PROCESSING = {
    "EXTRACTING_AUDIO",
    "CHUNKING_AUDIO",
    "TRANSCRIBING",
    "TRANSLATING",
    "GENERATING_SRT",
    "RENDERING",
}
_TERMINAL = {"DONE", "FAILED", "CANCELLED", "EXPIRED"}


def _validate_job_id(job_id: str) -> str:
    """Reject anything that is not a UUID (prevents path traversal via job_id)."""
    try:
        uuid.UUID(job_id)
    except (ValueError, TypeError) as exc:
        raise AgentError(404, "JOB_NOT_FOUND", "Job not found.") from exc
    return job_id


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AgentError(401, "UNAUTHORIZED", "Missing or invalid Authorization header.")
    return authorization[7:]


async def _authorize_mutation(settings: Settings, job_id: str, authorization: str | None) -> None:
    """Authorize a mutating job action (start/cancel).

    Accepts either this node's own token (constant-time compare) or the job's upload
    token (validated against the Control API, same path as upload).
    """
    token = _bearer(authorization)

    if settings.node_token and secrets.compare_digest(token, settings.node_token):
        return

    # Falls back to validating the short-lived upload token with the Control API.
    await validate_upload_token(settings, job_id, token)


@router.post("/{job_id}/start")
async def start_job(
    job_id: str,
    authorization: str | None = Header(None),
    node_state: NodeState = Depends(get_node_state),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Start the pipeline for an uploaded job.

    Preconditions: ``input.mp4`` exists under the job dir and this node's single-job
    slot is free or already held by this job (normally held since upload).
    """
    _validate_job_id(job_id)
    await _authorize_mutation(settings, job_id, authorization)

    job_dir = Path(settings.work_dir) / "jobs" / job_id
    input_path = job_dir / "input.mp4"
    if not input_path.exists():
        raise AgentError(
            404,
            "INPUT_NOT_FOUND",
            "Input video has not been uploaded for this job.",
            {"job_id": job_id},
        )

    registry = get_job_registry()
    existing = registry.get(job_id)
    if existing is not None and existing.status in _ACTIVE_PROCESSING:
        raise AgentError(
            409,
            "INVALID_JOB_STATUS",
            "Job is already being processed.",
            {"status": existing.status},
        )
    if existing is not None and existing.status == "DONE":
        raise AgentError(
            409,
            "INVALID_JOB_STATUS",
            "Job has already completed.",
            {"status": existing.status},
        )

    # Ensure this node's single-job slot belongs to this job.
    snap = node_state.snapshot()
    if snap.current_job_id is None:
        # Upload may have happened on a previous process lifetime, or via a path
        # that did not hold the slot — take it now (raises NODE_BUSY if lost).
        node_state.acquire_job(job_id)
    elif snap.current_job_id != job_id:
        raise AgentError(
            409,
            "NODE_BUSY",
            "This node is already processing another job.",
            {"current_job_id": snap.current_job_id},
        )

    registry.start(job_id, status="UPLOADED")
    start_pipeline_thread(job_id, settings)
    logger.info("Pipeline started for job %s", job_id)

    return JSONResponse(status_code=200, content={"status": "STARTED", "job_id": job_id})


@router.get("/{job_id}/status")
async def job_status(
    job_id: str,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Return local processing status/progress for a job.

    Falls back to disk inspection if there is no in-memory record (e.g. the agent
    restarted): a present output implies DONE, a present input implies UPLOADED.
    """
    _validate_job_id(job_id)

    rec = get_job_registry().get(job_id)
    if rec is not None:
        return JSONResponse(status_code=200, content=rec.as_status_dict())

    job_dir = Path(settings.work_dir) / "jobs" / job_id
    if (job_dir / "output" / "output.mp4").exists():
        body = {"job_id": job_id, "status": "DONE", "progress_percent": 100.0, "current_step": "DONE"}
        return JSONResponse(status_code=200, content=body)
    if (job_dir / "input.mp4").exists():
        body = {"job_id": job_id, "status": "UPLOADED", "progress_percent": 0.0, "current_step": None}
        return JSONResponse(status_code=200, content=body)

    raise AgentError(404, "JOB_NOT_FOUND", "Job not found on this node.", {"job_id": job_id})


@router.get("/{job_id}/download")
async def download_output(
    job_id: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Serve the rendered MP4 — only when the job is DONE.

    Authorization is the unguessable job UUID (capability URL). See Security notes.
    """
    _validate_job_id(job_id)

    job_dir = Path(settings.work_dir) / "jobs" / job_id
    output_path = job_dir / "output" / "output.mp4"

    rec = get_job_registry().get(job_id)
    if rec is not None and rec.status != "DONE":
        raise AgentError(
            409,
            "INVALID_JOB_STATUS",
            "Job output is not ready yet.",
            {"status": rec.status},
        )

    if not output_path.exists():
        raise AgentError(404, "JOB_NOT_FOUND", "Output not available for this job.", {"job_id": job_id})

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    authorization: str | None = Header(None),
    node_state: NodeState = Depends(get_node_state),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Best-effort cancel.

    If the pipeline is running, a cancel flag is set and honoured at the next pipeline
    step boundary (it does not kill an in-flight ffmpeg). If the job has not started
    processing yet, it is marked CANCELLED and the node slot is released immediately.
    """
    _validate_job_id(job_id)
    await _authorize_mutation(settings, job_id, authorization)

    registry = get_job_registry()
    rec = registry.get(job_id)

    if rec is not None and rec.status in _TERMINAL:
        raise AgentError(
            409,
            "INVALID_JOB_STATUS",
            "Job is already in a terminal state.",
            {"status": rec.status},
        )

    if rec is not None and rec.status in _ACTIVE_PROCESSING:
        registry.request_cancel(job_id)
        logger.info("Cancel requested for running job %s", job_id)
        return JSONResponse(
            status_code=202,
            content={"status": "CANCELLING", "job_id": job_id},
        )

    # Not actively processing: mark cancelled and release the slot now.
    registry.update(job_id, status="CANCELLED", current_step="CANCELLED")
    try:
        node_state.release_job(job_id)
    except AgentError:
        pass

    try:
        await notify_control_status(
            settings,
            job_id,
            status="CANCELLED",
            message="Job cancelled before processing.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to notify cancel for job %s: %s", job_id, exc)

    return JSONResponse(status_code=200, content={"status": "CANCELLED", "job_id": job_id})
