"""Nodes router — VPS agent heartbeat (Phase 06).

``POST /nodes/heartbeat`` is **node-authenticated**: the agent sends its
``node_id`` in the body and its node token as ``Authorization: Bearer <token>``.
The token is verified against the stored Argon2 hash (never logged, never
returned). See docs/specs/API_CONTRACT.md.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.dependencies import settings_dep
from ..config import Settings
from ..db.session import get_db
from ..errors import ApiError
from ..nodes import service as node_service
from ..schemas.nodes import HeartbeatRequest, HeartbeatResponse

router = APIRouter(prefix="/nodes", tags=["nodes"])


def _node_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise ApiError(401, "NODE_AUTH_FAILED", "Missing or malformed node token.")
    token = auth[len("Bearer ") :].strip()
    if not token:
        raise ApiError(401, "NODE_AUTH_FAILED", "Missing or malformed node token.")
    return token


@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    body: HeartbeatRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> HeartbeatResponse:
    """Receive and store a VPS agent heartbeat."""
    token = _node_bearer_token(request)
    node = node_service.authenticate_node(db, body.node_id, token)

    node = node_service.apply_heartbeat(
        db,
        node,
        status=body.status,
        current_job_id=body.current_job_id,
        cpu_percent=body.cpu_percent,
        ram_used_mb=body.ram_used_mb,
        ram_total_mb=body.ram_total_mb,
        disk_free_gb=body.disk_free_gb,
        agent_version=body.agent_version,
    )
    return HeartbeatResponse(ok=True, node_id=str(node.id), status=node.status.value)
