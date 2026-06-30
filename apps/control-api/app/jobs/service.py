"""Scheduler logic: job creation, node assignment, upload token generation.

Phase 07: Assigns jobs to idle nodes using transactional locking.
"""

from __future__ import annotations

import datetime as dt
import logging
import secrets
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.enums import JobStatus, NodeStatus
from ..db.models import Job, JobEvent, User, VpsNode
from ..errors import ApiError
from ..nodes.service import is_stale

logger = logging.getLogger(__name__)


# Pre-processing states where a job is waiting for (or performing) the browser
# upload. If the upload never completes (e.g. a 404/413 mid-upload) these get
# stuck and would otherwise count against the user's concurrent quota forever.
STALE_ELIGIBLE_STATUSES = (
    JobStatus.CREATED,
    JobStatus.ASSIGNED_NODE,
    JobStatus.WAITING_UPLOAD,
    JobStatus.UPLOADING,
)

# Truly active (non-terminal) states — these consume the concurrent-job quota.
ACTIVE_JOB_STATUSES = (
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
)

# Terminal states — a job here is finished and frees its node.
TERMINAL_JOB_STATUSES = (
    JobStatus.DONE,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.EXPIRED,
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def diagnose_no_node_available(db: Session, settings: Settings) -> list[dict]:
    """Return a per-node, non-secret explanation of why no node was assignable.

    Logged when assignment fails so NO_NODE_AVAILABLE is debuggable without
    exposing any token. Never raises.
    """
    from ..nodes.service import assignability_report

    try:
        nodes = list(db.scalars(select(VpsNode).where(VpsNode.deleted_at.is_(None))))
    except Exception:  # noqa: BLE001
        return []
    return [
        assignability_report(n, settings.node_heartbeat_stale_seconds) for n in nodes
    ]


def _hash_token(token: str) -> str:
    """Hash upload token with SHA-256."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def generate_upload_token() -> str:
    """Generate a cryptographically secure upload token."""
    return secrets.token_urlsafe(32)


def count_active_jobs(db: Session, user_id: uuid.UUID) -> int:
    """Count jobs in active (non-terminal) states for a user."""
    return db.scalar(
        select(text("count(*)"))
        .select_from(Job)
        .where(Job.user_id == user_id, Job.status.in_(ACTIVE_JOB_STATUSES))
    ) or 0


def count_daily_jobs(db: Session, user_id: uuid.UUID) -> int:
    """Count jobs that consume the user's *daily* quota (today, UTC).

    Only in-progress and successfully completed jobs count. FAILED/CANCELLED/
    EXPIRED attempts do NOT — so a failed upload never locks a user out for the
    rest of the day.
    """
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    counted = list(ACTIVE_JOB_STATUSES) + [JobStatus.DONE]
    return db.scalar(
        select(text("count(*)"))
        .select_from(Job)
        .where(
            Job.user_id == user_id,
            Job.created_at >= today_start,
            Job.status.in_(counted),
        )
    ) or 0


def pre_upload_active_job_ids(db: Session, user_id: uuid.UUID) -> list[str]:
    """Return ids of the user's active jobs still awaiting a completed upload.

    These are the prime suspects for a "stuck" job (browser upload failed) and
    are surfaced in the 409 details so the UI/admin can act on them.
    """
    rows = db.scalars(
        select(Job.id).where(
            Job.user_id == user_id,
            Job.status.in_(STALE_ELIGIBLE_STATUSES),
            Job.upload_completed_at.is_(None),
        )
    )
    return [str(r) for r in rows]


def _release_node_inline(db: Session, job: Job) -> None:
    """Clear the node slot for a job that has just entered a terminal state.

    Inline variant of :func:`release_node` that does NOT commit, so it can be
    used inside a batch transaction (e.g. expiring many stale jobs at once).
    """
    if job.node_id is None:
        return
    node = db.get(VpsNode, job.node_id)
    if node is None:
        return
    if node.current_job_id == job.id or node.current_job_id is None:
        node.current_job_id = None
        if node.status not in (NodeStatus.DISABLED, NodeStatus.OFFLINE):
            node.status = NodeStatus.IDLE
        node.updated_at = _now()


def expire_stale_jobs(
    db: Session, settings: Settings, user_id: uuid.UUID | None = None
) -> list[uuid.UUID]:
    """Auto-expire pre-upload jobs stuck past ``stale_job_timeout_minutes``.

    A job is stale when it sits in a pre-processing state, has no completed
    upload, and was created longer ago than the timeout. Each is moved to
    EXPIRED, its node is released, and a JobEvent is written. Scoped to one user
    when ``user_id`` is given, otherwise global (admin cleanup).

    Returns the list of expired job ids. Commits once.
    """
    cutoff = _now() - dt.timedelta(minutes=settings.stale_job_timeout_minutes)
    stmt = select(Job).where(
        Job.status.in_(STALE_ELIGIBLE_STATUSES),
        Job.upload_completed_at.is_(None),
        Job.created_at < cutoff,
    )
    if user_id is not None:
        stmt = stmt.where(Job.user_id == user_id)

    stale_jobs = list(db.scalars(stmt))
    expired_ids: list[uuid.UUID] = []
    for job in stale_jobs:
        previous = job.status.value
        job.status = JobStatus.EXPIRED
        job.error_code = "UPLOAD_TIMEOUT"
        job.error_message = (
            "Job expired: the video upload was not completed in time."
        )
        job.expires_at = _now()
        job.updated_at = _now()
        db.add(
            JobEvent(
                job_id=job.id,
                node_id=job.node_id,
                event_type="JOB_EXPIRED",
                message="Auto-expired stale job (upload never completed).",
                data={"previous_status": previous},
            )
        )
        _release_node_inline(db, job)
        expired_ids.append(job.id)

    if expired_ids:
        db.commit()
        logger.info(
            "Expired %d stale job(s): %s",
            len(expired_ids),
            [str(i) for i in expired_ids],
        )
    return expired_ids


def assign_idle_node(db: Session, settings: Settings) -> VpsNode | None:
    """Find and lock one idle, fresh node. Returns None if unavailable."""
    stale_threshold = _now() - dt.timedelta(seconds=settings.node_heartbeat_stale_seconds)

    node = db.scalar(
        select(VpsNode)
        .where(
            VpsNode.deleted_at.is_(None),
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
    from ..db.enums import UserRole

    # Check file size (applies to everyone, including admins)
    if file_size_bytes > user.max_file_mb * 1024 * 1024:
        raise ApiError(
            400,
            "FILE_TOO_LARGE",
            f"File exceeds the {user.max_file_mb}MB limit.",
            {"max_file_mb": user.max_file_mb, "file_size_bytes": file_size_bytes},
        )

    # Reconcile abandoned upload attempts BEFORE counting quota, so a failed
    # browser upload (404/413) that left a job stuck never blocks a new job.
    expire_stale_jobs(db, settings, user_id=user.id)

    # Root admins are exempt from quota limits.
    if user.role != UserRole.ADMIN:
        active_count = count_active_jobs(db, user.id)
        daily_count = count_daily_jobs(db, user.id)
        stuck_ids = pre_upload_active_job_ids(db, user.id)
        quota_details = {
            "active_jobs_count": active_count,
            "active_jobs_limit": user.max_concurrent_jobs,
            "daily_jobs_count": daily_count,
            "daily_jobs_limit": user.daily_job_limit,
            "stuck_job_ids": stuck_ids,
        }

        # Concurrent-job limit.
        if active_count >= user.max_concurrent_jobs:
            raise ApiError(
                409,
                "USER_LIMIT_REACHED",
                f"Bạn đang có {active_count}/{user.max_concurrent_jobs} job đang chạy. "
                "Hãy đợi job hiện tại xong hoặc hủy job bị kẹt rồi thử lại.",
                quota_details,
            )

        # Daily-job limit (0 == unlimited).
        if user.daily_job_limit > 0 and daily_count >= user.daily_job_limit:
            raise ApiError(
                409,
                "DAILY_LIMIT_REACHED",
                f"Bạn đã đạt giới hạn {user.daily_job_limit} job trong ngày hôm nay. "
                "Vui lòng thử lại vào ngày mai.",
                quota_details,
            )

    # Assign node transactionally
    node = assign_idle_node(db, settings)
    if node is None:
        # Log a non-secret diagnostic so operators can see *why* (stale / busy /
        # disabled / no nodes at all) without querying the DB by hand.
        diag = diagnose_no_node_available(db, settings)
        logger.warning("NO_NODE_AVAILABLE: no assignable node. diagnostics=%s", diag)
        raise ApiError(
            409,
            "NO_NODE_AVAILABLE",
            "No idle VPS nodes are available. Please try again later.",
            {"nodes": diag},
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
    """Release the node assigned to a job when the job reaches a terminal state.

    Terminal = DONE/FAILED/CANCELLED/EXPIRED.

    Always clears ``current_job_id`` for the matching job so the node can never be
    left holding a phantom job (a common cause of NO_NODE_AVAILABLE). The status
    transition is handled carefully:

    - DISABLED: keep DISABLED (admin override) but still clear current_job_id.
    - OFFLINE: keep OFFLINE (the next heartbeat will move it to IDLE) but still
      clear current_job_id so a returning node is immediately assignable.
    - Otherwise: move to IDLE.
    """
    terminal_statuses = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.EXPIRED}
    if job.status not in terminal_statuses:
        return

    if job.node_id is None:
        return

    node = db.get(VpsNode, job.node_id)
    if node is None:
        return

    # Only clear the slot if it actually points at this job (avoid stomping a
    # newer assignment) — but if it's None already, that's fine too.
    if node.current_job_id == job.id or node.current_job_id is None:
        node.current_job_id = None
        if node.status not in (NodeStatus.DISABLED, NodeStatus.OFFLINE):
            node.status = NodeStatus.IDLE
        node.updated_at = _now()
        db.commit()


def _terminate_job(
    db: Session,
    job_id: str,
    new_status: JobStatus,
    event_type: str,
    error_code: str,
    error_message: str,
) -> Job:
    """Force a job into a terminal state (admin action) and free its node.

    Idempotent: a job already in a terminal state is returned unchanged.
    """
    job = get_job(db, job_id, user=None)
    if job.status in TERMINAL_JOB_STATUSES:
        return job

    job.status = new_status
    job.error_code = error_code
    job.error_message = error_message
    job.completed_at = _now()
    job.updated_at = _now()
    db.add(
        JobEvent(
            job_id=job.id,
            node_id=job.node_id,
            event_type=event_type,
            message=error_message,
        )
    )
    db.commit()
    db.refresh(job)

    # release_node only acts on terminal jobs, which this now is.
    release_node(db, job)
    db.refresh(job)
    return job


def admin_cancel_job(db: Session, job_id: str) -> Job:
    """Admin: cancel a job and release its node."""
    return _terminate_job(
        db,
        job_id,
        JobStatus.CANCELLED,
        "JOB_CANCELLED",
        "CANCELLED_BY_ADMIN",
        "Job cancelled by administrator.",
    )


def admin_mark_failed(db: Session, job_id: str, reason: str | None = None) -> Job:
    """Admin: mark a job as FAILED and release its node."""
    return _terminate_job(
        db,
        job_id,
        JobStatus.FAILED,
        "JOB_MARKED_FAILED",
        "MARKED_FAILED_BY_ADMIN",
        reason or "Job marked as failed by administrator.",
    )


def cleanup_stale_jobs(db: Session, settings: Settings) -> list[str]:
    """Admin: expire all stuck pre-upload jobs across every user."""
    return [str(i) for i in expire_stale_jobs(db, settings, user_id=None)]
