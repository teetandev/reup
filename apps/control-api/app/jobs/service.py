"""Scheduler logic: job creation, node assignment, upload token generation.

Phase 07: Assigns jobs to idle nodes using transactional locking.
"""

from __future__ import annotations

import datetime as dt
import secrets
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.enums import JobStatus, NodeStatus
from ..db.models import Job, JobEvent, User, VpsNode
from ..errors import ApiError
from ..nodes.service import is_stale


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _hash_token(token: str) -> str:
    """Hash upload token with SHA-256."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def generate_upload_token() -> str:
    """Generate a cryptographically secure upload token."""
    return secrets.token_urlsafe(32)


def count_active_jobs(db: Session, user_id: uuid.UUID) -> int:
    """Count jobs in active (non-terminal) states for a user."""
    active_statuses = [
        JobStatus.ASSIGNED_NODE,
        JobStatus.WAITING_UPLOAD,
        JobStatus.UPLOADING,
        JobStatus.UPLOADED,
        JobStatus.EXTRACTING_AUDIO,
        JobStatus.CHUNKING_AUDIO,
        JobStatus.TRANSCRIBING,
        JobStatus.TRANSLATING,
        JobStatus.GENERATING_SRT,
        JobStatus.RENDERING,
    ]
    return db.scalar(
        select(text("count(*)"))
        .select_from(Job)
        .where(Job.user_id == user_id, Job.status.in_(active_statuses))
    ) or 0


def assign_idle_node(db: Session, settings: Settings) -> VpsNode | None:
    """Find and lock one idle, fresh node. Returns None if unavailable."""
    stale_threshold = _now() - dt.timedelta(seconds=settings.node_heartbeat_stale_seconds)

    node = db.scalar(
        select(VpsNode)
        .where(
            VpsNode.enabled == True,
            VpsNode.status == NodeStatus.IDLE,
            VpsNode.current_job_id == None,
            VpsNode.last_heartbeat_at > stale_threshold,
        )
        .order_by(VpsNode.last_heartbeat_at.desc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    return node


def create_job(
    db: Session,
    settings: Settings,
    user: User,
    api_key_id: uuid.UUID,
    original_filename: str,
    file_size_bytes: int,
) -> tuple[Job, str]:
    """Create a job and assign a node. Returns (job, plaintext_upload_token).

    Raises ApiError on validation failure or no node available.
    """
    # Check file size
    if file_size_bytes > user.max_file_mb * 1024 * 1024:
        raise ApiError(
            400,
            "FILE_TOO_LARGE",
            f"File exceeds the {user.max_file_mb}MB limit.",
            {"max_file_mb": user.max_file_mb, "file_size_bytes": file_size_bytes},
        )

    # Check active job limit
    active_count = count_active_jobs(db, user.id)
    if active_count >= user.max_concurrent_jobs:
        raise ApiError(
            409,
            "USER_LIMIT_REACHED",
            f"User has reached the limit of {user.max_concurrent_jobs} concurrent jobs.",
            {"max_concurrent_jobs": user.max_concurrent_jobs, "active_jobs": active_count},
        )

    # Assign node transactionally
    node = assign_idle_node(db, settings)
    if node is None:
        raise ApiError(
            409,
            "NO_NODE_AVAILABLE",
            "No idle VPS nodes are available. Please try again later.",
        )

    # Generate upload token
    upload_token = generate_upload_token()
    token_hash = _hash_token(upload_token)
    token_expires_at = _now() + dt.timedelta(minutes=settings.upload_token_expires_minutes)

    # Create job
    job = Job(
        user_id=user.id,
        api_key_id=api_key_id,
        node_id=node.id,
        status=JobStatus.WAITING_UPLOAD,
        original_filename=original_filename,
        file_size_bytes=file_size_bytes,
        upload_token_hash=token_hash,
        upload_token_expires_at=token_expires_at,
        node_upload_url=f"{node.public_url.rstrip('/')}/jobs/{str(uuid.uuid4())}/upload",
        assigned_at=_now(),
    )
    db.add(job)
    db.flush()

    # Update node to BUSY
    node.status = NodeStatus.BUSY
    node.current_job_id = job.id
    node.updated_at = _now()

    # Create job event
    event = JobEvent(
        job_id=job.id,
        node_id=node.id,
        event_type="JOB_CREATED",
        message=f"Job created and assigned to node {node.name}",
        data={"node_id": str(node.id), "node_name": node.name},
    )
    db.add(event)

    db.commit()
    db.refresh(job)

    # Fix upload URL with actual job ID
    job.node_upload_url = f"{node.public_url.rstrip('/')}/jobs/{job.id}/upload"
    db.commit()
    db.refresh(job)

    return job, upload_token


def get_job(db: Session, job_id: str, user: User | None) -> Job:
    """Get a job by ID. User can only see own jobs; admin sees all."""
    try:
        jid = uuid.UUID(job_id)
    except (ValueError, TypeError) as exc:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found.") from exc

    job = db.get(Job, jid)
    if job is None:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found.")

    # Authorization check
    if user is not None and job.user_id != user.id:
        from ..db.enums import UserRole
        if user.role != UserRole.ADMIN:
            raise ApiError(403, "JOB_NOT_OWNED", "You do not have access to this job.")

    return job


def list_user_jobs(db: Session, user_id: uuid.UUID) -> list[Job]:
    """List all jobs for a user, newest first."""
    return list(
        db.scalars(
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
        )
    )


def release_node(db: Session, job: Job) -> None:
    """Release the node assigned to a job (set IDLE, clear current_job_id).

    Only releases if job is in a terminal state and node is not DISABLED/OFFLINE.
    """
    terminal_statuses = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.EXPIRED}
    if job.status not in terminal_statuses:
        return

    if job.node_id is None:
        return

    node = db.get(VpsNode, job.node_id)
    if node is None:
        return

    # Don't touch DISABLED/OFFLINE nodes
    if node.status in (NodeStatus.DISABLED, NodeStatus.OFFLINE):
        return

    node.status = NodeStatus.IDLE
    node.current_job_id = None
    node.updated_at = _now()
    db.commit()
