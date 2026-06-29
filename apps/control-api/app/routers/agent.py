"""Agent callback router: node-authenticated endpoints for VPS agents.

Phase 08: Implements POST /jobs/{job_id}/validate-token and POST /jobs/{job_id}/agent-status.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db.models import Job, JobEvent, VpsNode
from ..db.session import get_db
from ..errors import ApiError
from ..jobs.service import get_job, release_node, _hash_token
from ..schemas.agent import (
    AgentStatusUpdateRequest,
    AgentStatusUpdateResponse,
    ValidateTokenRequest,
    ValidateTokenResponse,
)

router = APIRouter(prefix="/jobs", tags=["agent-callbacks"])


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _verify_node_auth(authorization: str | None, job: Job, db: Session) -> VpsNode:
    """Verify node token and ensure this node owns the job."""
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "Missing or invalid Authorization header.")

    node_token = authorization[7:]  # Remove "Bearer "

    # Get the node assigned to this job
    if job.node_id is None:
        raise ApiError(403, "FORBIDDEN", "Job has no assigned node.")

    node = db.get(VpsNode, job.node_id)
    if node is None:
        raise ApiError(404, "NODE_NOT_FOUND", "Assigned node not found.")

    # Verify with Argon2 (matches node_tokens.py storage)
    from ..auth.node_tokens import verify_node_token
    if not verify_node_token(node_token, node.node_token_hash):
        raise ApiError(403, "NODE_AUTH_FAILED", "Invalid node token.")

    return node


@router.post("/{job_id}/validate-token", response_model=ValidateTokenResponse)
def validate_upload_token(
    job_id: str,
    req: ValidateTokenRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ValidateTokenResponse:
    """Validate upload token for a job.

    Called by VPS Agent to verify upload token before accepting file upload.
    Requires node authentication.
    """
    # Parse job_id
    try:
        jid = uuid.UUID(job_id)
    except (ValueError, TypeError) as exc:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found.") from exc

    job = db.get(Job, jid)
    if job is None:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found.")

    # Verify node token
    node = _verify_node_auth(authorization, job, db)

    # Validate upload token
    token_hash = _hash_token(req.upload_token)

    if job.upload_token_hash != token_hash:
        raise ApiError(401, "UPLOAD_TOKEN_INVALID", "Invalid upload token.")

    # Check expiry
    now = _now()
    if job.upload_token_expires_at is None or now > job.upload_token_expires_at:
        raise ApiError(401, "UPLOAD_TOKEN_EXPIRED", "Upload token has expired.")

    return ValidateTokenResponse(
        valid=True,
        job_id=job.id,
        user_id=job.user_id,
        node_id=node.id,
    )


@router.post("/{job_id}/agent-status", response_model=AgentStatusUpdateResponse)
def update_job_status(
    job_id: str,
    req: AgentStatusUpdateRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> AgentStatusUpdateResponse:
    """Update job status from VPS agent.

    Node-authenticated callback. Only the assigned node can update job status.
    """
    # Parse job_id
    try:
        jid = uuid.UUID(job_id)
    except (ValueError, TypeError) as exc:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found.") from exc

    job = db.get(Job, jid)
    if job is None:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found.")

    # Verify node token
    node = _verify_node_auth(authorization, job, db)

    # Update job fields
    now = _now()
    old_status = job.status

    if req.status is not None:
        job.status = req.status

    if req.current_step is not None:
        job.current_step = req.current_step

    if req.progress_percent is not None:
        job.progress_percent = req.progress_percent

    if req.duration_seconds is not None:
        job.duration_seconds = req.duration_seconds

    if req.resolution is not None:
        job.resolution = req.resolution

    if req.error_code is not None:
        job.error_code = req.error_code

    if req.error_message is not None:
        job.error_message = req.error_message

    # Update timestamps based on status
    if req.status:
        from ..db.enums import JobStatus

        if req.status == JobStatus.UPLOADING and job.upload_started_at is None:
            job.upload_started_at = now

        if req.status == JobStatus.UPLOADED and job.upload_completed_at is None:
            job.upload_completed_at = now

        if req.status in {JobStatus.EXTRACTING_AUDIO, JobStatus.CHUNKING_AUDIO, JobStatus.TRANSCRIBING,
                          JobStatus.TRANSLATING, JobStatus.GENERATING_SRT, JobStatus.RENDERING}:
            if job.processing_started_at is None:
                job.processing_started_at = now

        if req.status in {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}:
            if job.completed_at is None:
                job.completed_at = now

        # Phase 11 compat: expose the agent download URL to the web UI once the
        # output exists. Derived from the node's public_url (never the upload token).
        if req.status == JobStatus.DONE and job.node_download_url is None:
            job.node_download_url = f"{node.public_url.rstrip('/')}/jobs/{job.id}/download"

    job.updated_at = now

    # Create event
    event = JobEvent(
        job_id=job.id,
        node_id=node.id,
        event_type=f"STATUS_{req.status.value}" if req.status else "STATUS_UPDATE",
        message=req.message or f"Job status updated to {req.status.value if req.status else 'unchanged'}",
        data=req.metadata or {},
    )
    db.add(event)

    db.commit()
    db.refresh(job)

    # Release the node back to IDLE when the job reaches a terminal state
    # (Phase 10: DONE/FAILED/CANCELLED/EXPIRED). release_node is a no-op for
    # non-terminal statuses and never disturbs DISABLED/OFFLINE nodes.
    release_node(db, job)
    db.refresh(job)

    return AgentStatusUpdateResponse(
        job_id=job.id,
        status=job.status,
        updated_at=job.updated_at,
    )
