"""Node registry, heartbeat upsert, authentication, and stale detection.

Coordination-only logic for the ``vps_nodes`` table (DATABASE_SCHEMA.md).
No FFmpeg, no upload, no scheduler here — those live in later phases.

Stale detection rule (CLAUDE.md / ACCEPTANCE_CRITERIA Phase 06): a node whose
``last_heartbeat_at`` is older than ``NODE_HEARTBEAT_STALE_SECONDS`` is treated
as **OFFLINE**. We persist that transition when nodes are listed/fetched so the
admin view and the (future) scheduler agree on reality.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.node_tokens import (
    generate_node_token,
    hash_node_token,
    node_token_prefix,
    verify_node_token,
)
from ..config import Settings
from ..db.enums import NodeStatus
from ..db.models import VpsNode
from ..errors import ApiError
from ..schemas.nodes import AGENT_REPORTABLE_STATUSES


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_node_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError) as exc:
        raise ApiError(404, "NODE_NOT_FOUND", "Node not found.") from exc


def build_install_command(settings: Settings, node_id: uuid.UUID, token: str, public_url: str) -> str:
    """Build the one-line VPS install command (see VPS_PROVISIONING.md).

    The plaintext token appears only here, in the response shown once to the
    admin. It is never persisted or logged.
    """
    base = settings.control_api_public_url.rstrip("/")
    return (
        f"curl -fsSL {base}/install-node.sh | bash -s -- "
        f"--node-id {node_id} "
        f"--node-token {token} "
        f"--control-api-url {base} "
        f"--public-url {public_url}"
    )


def register_node(db: Session, settings: Settings, name: str, public_url: str) -> tuple[VpsNode, str]:
    """Create a node and issue its token. Returns ``(node, plaintext_token)``.

    Only ``node_token_prefix`` + ``node_token_hash`` are stored. The plaintext
    token is returned to the caller for one-time display and then discarded.
    """
    existing = db.scalar(select(VpsNode).where(VpsNode.public_url == public_url))
    if existing is not None:
        raise ApiError(
            409,
            "CONFLICT",
            "A node with this public_url already exists.",
            {"public_url": public_url},
        )

    token = generate_node_token()
    node = VpsNode(
        name=name,
        public_url=public_url,
        status=NodeStatus.PROVISIONING,
        node_token_prefix=node_token_prefix(token),
        node_token_hash=hash_node_token(token),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node, token


def is_stale(node: VpsNode, stale_seconds: int, now: dt.datetime | None = None) -> bool:
    """True if the node has heartbeated before but not within the stale window.

    A node that has never heartbeated (``last_heartbeat_at is None``) is not
    considered stale — it is simply still PROVISIONING.
    """
    if node.last_heartbeat_at is None:
        return False
    now = now or _now()
    last = node.last_heartbeat_at
    if last.tzinfo is None:  # be robust to naive timestamps from some drivers
        last = last.replace(tzinfo=dt.timezone.utc)
    return (now - last).total_seconds() > stale_seconds


def reconcile_stale(db: Session, node: VpsNode, stale_seconds: int) -> VpsNode:
    """Mark a stale node OFFLINE (unless DISABLED), persisting the change.

    DISABLED is an explicit admin state and is never overridden by staleness.
    """
    if node.status == NodeStatus.DISABLED:
        return node
    if node.status != NodeStatus.OFFLINE and is_stale(node, stale_seconds):
        node.status = NodeStatus.OFFLINE
        node.updated_at = _now()
        db.commit()
        db.refresh(node)
    return node


def list_nodes(db: Session, stale_seconds: int) -> list[VpsNode]:
    """Return all nodes, reconciling stale ones to OFFLINE first."""
    nodes = list(db.scalars(select(VpsNode).order_by(VpsNode.created_at.desc())))
    for node in nodes:
        reconcile_stale(db, node, stale_seconds)
    return nodes


def get_node(db: Session, node_id: str, stale_seconds: int) -> VpsNode:
    """Fetch a node by id, reconciling staleness. Raises NODE_NOT_FOUND."""
    nid = _parse_node_id(node_id)
    node = db.get(VpsNode, nid)
    if node is None:
        raise ApiError(404, "NODE_NOT_FOUND", "Node not found.")
    return reconcile_stale(db, node, stale_seconds)


def authenticate_node(db: Session, node_id: str, token: str) -> VpsNode:
    """Authenticate a VPS agent by ``node_id`` + node token.

    Returns the node on success. Raises ``NODE_AUTH_FAILED`` for an unknown
    node, a node with no token set, or a bad token — without distinguishing
    between them, to avoid node enumeration.
    """
    try:
        nid = uuid.UUID(node_id)
    except (ValueError, TypeError):
        raise ApiError(401, "NODE_AUTH_FAILED", "Node authentication failed.")

    node = db.get(VpsNode, nid)
    if node is None or not verify_node_token(token, node.node_token_hash):
        raise ApiError(401, "NODE_AUTH_FAILED", "Node authentication failed.")
    return node


def apply_heartbeat(
    db: Session,
    node: VpsNode,
    *,
    status: str,
    current_job_id: str | None,
    cpu_percent: float | None,
    ram_used_mb: int | None,
    ram_total_mb: int | None,
    disk_free_gb: float | None,
    agent_version: str | None,
) -> VpsNode:
    """Upsert heartbeat fields onto an authenticated node.

    The agent may only self-report IDLE/BUSY/ERROR. A DISABLED node keeps its
    DISABLED status (admin override) but still records fresh resource/liveness
    data so the admin can see it is alive.
    """
    if status not in AGENT_REPORTABLE_STATUSES:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Invalid heartbeat status.",
            {"status": status, "allowed": sorted(AGENT_REPORTABLE_STATUSES)},
        )

    job_uuid: uuid.UUID | None = None
    if current_job_id:
        try:
            job_uuid = uuid.UUID(current_job_id)
        except (ValueError, TypeError) as exc:
            raise ApiError(
                422, "VALIDATION_ERROR", "Invalid current_job_id.", {"current_job_id": current_job_id}
            ) from exc

    if node.status != NodeStatus.DISABLED:
        node.status = NodeStatus(status)
    node.current_job_id = job_uuid
    node.cpu_percent = cpu_percent
    node.ram_used_mb = ram_used_mb
    node.ram_total_mb = ram_total_mb
    node.disk_free_gb = disk_free_gb
    if agent_version is not None:
        node.agent_version = agent_version
    node.last_heartbeat_at = _now()
    node.updated_at = _now()

    db.commit()
    db.refresh(node)
    return node
