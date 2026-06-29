"""Admin router — user creation and secret-key issuing/revoking.

Admin auth: ``X-Admin-Secret`` (bootstrap) header or an admin Bearer JWT
(see app/auth/dependencies.py::require_admin). Node management lands in Phase 06.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..auth.dependencies import require_admin, settings_dep
from ..auth.keys import generate_secret_key, hash_key, key_prefix
from ..config import Settings
from ..db.enums import ApiKeyStatus, UserRole
from ..db.models import ApiKey, Job, User, VpsNode
from ..db.session import get_db
from ..errors import ApiError
from ..nodes import service as node_service
from ..schemas.admin import (
    CreateUserRequest,
    IssueKeyRequest,
    IssueKeyResponse,
    RevokeKeyResponse,
    UserResponse,
)
from ..schemas.nodes import NodeResponse, RegisterNodeRequest, RegisterNodeResponse

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _parse_uuid(value: str, not_found_message: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError) as exc:
        raise ApiError(404, "NOT_FOUND", not_found_message) from exc


def _node_response(node: VpsNode) -> NodeResponse:
    """Serialize a node for the admin view. Never exposes the token hash."""
    return NodeResponse(
        id=str(node.id),
        name=node.name,
        public_url=node.public_url,
        status=node.status.value,
        enabled=node.enabled,
        max_jobs=node.max_jobs,
        current_job_id=str(node.current_job_id) if node.current_job_id else None,
        node_token_prefix=node.node_token_prefix,
        agent_version=node.agent_version,
        cpu_percent=float(node.cpu_percent) if node.cpu_percent is not None else None,
        ram_used_mb=node.ram_used_mb,
        ram_total_mb=node.ram_total_mb,
        disk_free_gb=float(node.disk_free_gb) if node.disk_free_gb is not None else None,
        last_heartbeat_at=node.last_heartbeat_at,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        display_name=user.display_name,
        role=user.role.value,
        status=user.status.value,
        max_file_mb=user.max_file_mb,
        max_concurrent_jobs=user.max_concurrent_jobs,
        daily_job_limit=user.daily_job_limit,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(body: CreateUserRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Create a user (admin only)."""
    user = User(
        display_name=body.display_name,
        role=UserRole(body.role),
        max_file_mb=body.max_file_mb,
        daily_job_limit=body.daily_job_limit,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.post("/users/{user_id}/keys", response_model=IssueKeyResponse, status_code=201)
def issue_key(
    user_id: str, body: IssueKeyRequest, db: Session = Depends(get_db)
) -> IssueKeyResponse:
    """Issue a new secret key for a user. Plaintext key is returned ONCE."""
    uid = _parse_uuid(user_id, "User not found.")
    user = db.get(User, uid)
    if user is None:
        raise ApiError(404, "NOT_FOUND", "User not found.")

    secret = generate_secret_key()
    key = ApiKey(
        user_id=user.id,
        key_prefix=key_prefix(secret),
        key_hash=hash_key(secret),
        name=body.name,
        status=ApiKeyStatus.ACTIVE,
    )
    db.add(key)
    db.commit()
    # Returned once; only the hash + prefix are persisted.
    return IssueKeyResponse(secret_key=secret, key_prefix=key.key_prefix)


@router.post("/keys/{key_id}/revoke", response_model=RevokeKeyResponse)
def revoke_key(key_id: str, db: Session = Depends(get_db)) -> RevokeKeyResponse:
    """Revoke a secret key so it can no longer be used to log in."""
    kid = _parse_uuid(key_id, "Key not found.")
    key = db.get(ApiKey, kid)
    if key is None:
        raise ApiError(404, "NOT_FOUND", "Key not found.")

    if key.status != ApiKeyStatus.REVOKED:
        key.status = ApiKeyStatus.REVOKED
        key.revoked_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    return RevokeKeyResponse(id=str(key.id), status=key.status.value)


@router.post("/nodes", response_model=RegisterNodeResponse, status_code=201)
def register_node(
    body: RegisterNodeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> RegisterNodeResponse:
    """Register a VPS node and issue its token.

    The plaintext ``node_token`` is returned ONCE (inside ``install_command``);
    only its hash + prefix are persisted.
    """
    node, token = node_service.register_node(db, settings, body.name, body.public_url)
    install_command = node_service.build_install_command(
        settings, node.id, token, node.public_url
    )
    return RegisterNodeResponse(
        id=str(node.id),
        name=node.name,
        public_url=node.public_url,
        status=node.status.value,
        node_token=token,
        node_token_prefix=node.node_token_prefix or "",
        install_command=install_command,
    )


@router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(
    db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
) -> list[NodeResponse]:
    """List all nodes. Stale nodes are reconciled to OFFLINE first."""
    nodes = node_service.list_nodes(db, settings.node_heartbeat_stale_seconds)
    return [_node_response(n) for n in nodes]


@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node(
    node_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> NodeResponse:
    """View a single node's detail. Reconciles staleness to OFFLINE."""
    node = node_service.get_node(db, node_id, settings.node_heartbeat_stale_seconds)
    return _node_response(node)


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    """List all users."""
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    return [_user_response(u) for u in users]


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    """Admin dashboard stats."""
    import datetime as dt
    from ..db.enums import JobStatus, NodeStatus

    stale_threshold = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=settings.node_heartbeat_stale_seconds)
    today_start = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = db.scalar(select(text("count(*)")).select_from(User)) or 0
    active_jobs = db.scalar(
        select(text("count(*)"))
        .select_from(Job)
        .where(Job.status.in_([
            JobStatus.ASSIGNED_NODE, JobStatus.WAITING_UPLOAD, JobStatus.UPLOADING,
            JobStatus.UPLOADED, JobStatus.EXTRACTING_AUDIO, JobStatus.CHUNKING_AUDIO,
            JobStatus.TRANSCRIBING, JobStatus.TRANSLATING, JobStatus.GENERATING_SRT, JobStatus.RENDERING
        ]))
    ) or 0
    idle_nodes = db.scalar(
        select(text("count(*)"))
        .select_from(VpsNode)
        .where(VpsNode.enabled == True, VpsNode.status == NodeStatus.IDLE, VpsNode.last_heartbeat_at > stale_threshold)
    ) or 0
    busy_nodes = db.scalar(
        select(text("count(*)"))
        .select_from(VpsNode)
        .where(VpsNode.enabled == True, VpsNode.status == NodeStatus.BUSY, VpsNode.last_heartbeat_at > stale_threshold)
    ) or 0
    offline_nodes = db.scalar(
        select(text("count(*)"))
        .select_from(VpsNode)
        .where(VpsNode.status == NodeStatus.OFFLINE)
    ) or 0
    failed_jobs_today = db.scalar(
        select(text("count(*)"))
        .select_from(Job)
        .where(Job.status == JobStatus.FAILED, Job.created_at >= today_start)
    ) or 0

    return {
        "total_users": total_users,
        "active_jobs": active_jobs,
        "idle_nodes": idle_nodes,
        "busy_nodes": busy_nodes,
        "offline_nodes": offline_nodes,
        "failed_jobs_today": failed_jobs_today,
    }


@router.get("/jobs")
def list_all_jobs(db: Session = Depends(get_db)):
    """List all jobs for admin (not just own jobs)."""
    from ..schemas.jobs import JobResponse
    jobs = list(db.scalars(select(Job).order_by(Job.created_at.desc())))
    return {"jobs": [JobResponse.model_validate(j) for j in jobs]}
