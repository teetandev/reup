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
    existing = db.scalar(
        select(VpsNode).where(
            VpsNode.public_url == public_url, VpsNode.deleted_at.is_(None)
        )
    )
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
    """Return all *non-deleted* nodes, reconciling stale ones to OFFLINE first.

    Soft-deleted nodes (``deleted_at IS NOT NULL``) are hidden from the admin
    list — their job history is kept but they are gone from the operator view.
    """
    nodes = list(
        db.scalars(
            select(VpsNode)
            .where(VpsNode.deleted_at.is_(None))
            .order_by(VpsNode.created_at.desc())
        )
    )
    for node in nodes:
        reconcile_stale(db, node, stale_seconds)
    return nodes


def get_node(db: Session, node_id: str, stale_seconds: int) -> VpsNode:
    """Fetch a non-deleted node by id, reconciling staleness.

    Raises NODE_NOT_FOUND for an unknown id *or* a soft-deleted node, so a
    deleted node behaves as if it no longer exists for all admin operations.
    """
    nid = _parse_node_id(node_id)
    node = db.get(VpsNode, nid)
    if node is None or node.deleted_at is not None:
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
    # A soft-deleted node must not be able to authenticate / heartbeat again.
    if (
        node is None
        or node.deleted_at is not None
        or not verify_node_token(token, node.node_token_hash)
    ):
        raise ApiError(401, "NODE_AUTH_FAILED", "Node authentication failed.")
    return node


def heartbeat_age_seconds(node: VpsNode, now: dt.datetime | None = None) -> float | None:
    """Seconds since the node's last heartbeat, or None if it never heartbeated."""
    if node.last_heartbeat_at is None:
        return None
    now = now or _now()
    last = node.last_heartbeat_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=dt.timezone.utc)
    return (now - last).total_seconds()


def assignability_report(node: VpsNode, stale_seconds: int) -> dict:
    """Explain whether a node can currently be assigned a job, and why not.

    Used by the admin debug endpoint and the NO_NODE_AVAILABLE runbook. Exposes
    only non-secret operational fields.
    """
    reasons: list[str] = []

    if not node.enabled:
        reasons.append("disabled")
    if node.status != NodeStatus.IDLE:
        reasons.append(f"status_not_idle ({node.status.value})")
    if node.current_job_id is not None:
        reasons.append("current_job_id_not_null")

    age = heartbeat_age_seconds(node)
    if age is None:
        reasons.append("never_heartbeated")
    elif age > stale_seconds:
        reasons.append(f"stale_heartbeat ({int(age)}s > {stale_seconds}s)")

    return {
        "node_id": str(node.id),
        "name": node.name,
        "enabled": node.enabled,
        "status": node.status.value,
        "current_job_id": str(node.current_job_id) if node.current_job_id else None,
        "last_heartbeat_at": node.last_heartbeat_at.isoformat()
        if node.last_heartbeat_at
        else None,
        "heartbeat_age_seconds": int(age) if age is not None else None,
        "stale_threshold_seconds": stale_seconds,
        "assignable": len(reasons) == 0,
        "reasons": reasons,
    }


def set_node_enabled(db: Session, node: VpsNode, enabled: bool, stale_seconds: int) -> VpsNode:
    """Enable or disable a node (admin override).

    - Disable: set ``enabled=False`` and status DISABLED so the scheduler skips it.
    - Enable: set ``enabled=True``; status becomes IDLE if a recent heartbeat
      exists, otherwise PROVISIONING (until the next heartbeat arrives).
    """
    node.enabled = enabled
    if not enabled:
        node.status = NodeStatus.DISABLED
    else:
        # Re-derive a sensible status from liveness.
        if node.last_heartbeat_at is not None and not is_stale(node, stale_seconds):
            node.status = NodeStatus.IDLE if node.current_job_id is None else NodeStatus.BUSY
        else:
            node.status = NodeStatus.PROVISIONING
    node.updated_at = _now()
    db.commit()
    db.refresh(node)
    return node


def rotate_node_token(db: Session, node: VpsNode) -> tuple[VpsNode, str]:
    """Issue a fresh node token, invalidating the old one. Returns plaintext once.

    Only the new hash + prefix are persisted; the previous hash is overwritten so
    the old token can no longer authenticate.
    """
    token = generate_node_token()
    node.node_token_prefix = node_token_prefix(token)
    node.node_token_hash = hash_node_token(token)
    node.updated_at = _now()
    db.commit()
    db.refresh(node)
    return node, token


def delete_node(db: Session, node: VpsNode, force: bool = False) -> None:
    """Soft-delete a node. Refuses a BUSY node unless ``force=True``.

    This is a **logical** delete: the row is kept so that all existing jobs and
    job_events keep referencing it (job history is preserved — exactly what the
    admin modal promises), but the node becomes invisible and unusable:

    - ``deleted_at`` is stamped (hides it from the admin list and ``get_node``).
    - ``status`` -> DISABLED and ``enabled`` -> False (scheduler never picks it).
    - ``current_job_id`` is cleared so it never holds a phantom job.
    - the node token is wiped (prefix + hash) so the old agent can no longer
      authenticate or heartbeat back to life.
    - ``public_url`` is suffixed with ``#deleted-<id>`` so the (unique) URL is
      freed for a brand-new node to reuse — this is what stops jobs from being
      routed to the dead Codespace URL.

    No hard ``DELETE`` is issued, so there is no FK violation and no 500. The
    ON DELETE SET NULL rules added in migration 0002 remain as a safety net if a
    hard delete is ever performed manually.
    """
    if node.deleted_at is not None:
        # Idempotent: deleting an already-deleted node is a no-op success.
        return

    if node.status == NodeStatus.BUSY and not force:
        raise ApiError(
            409,
            "NODE_BUSY",
            "Node is BUSY. Use force=true to delete it anyway.",
            {
                "node_id": str(node.id),
                "current_job_id": str(node.current_job_id) if node.current_job_id else None,
            },
        )

    now = _now()
    node.deleted_at = now
    node.status = NodeStatus.DISABLED
    node.enabled = False
    node.current_job_id = None
    # Invalidate the token so the dead agent cannot reconnect.
    node.node_token_prefix = None
    node.node_token_hash = None
    # Free the unique public_url so a replacement node can register the same URL.
    if node.public_url and "#deleted-" not in node.public_url:
        node.public_url = f"{node.public_url}#deleted-{node.id}"
    node.updated_at = now

    db.commit()


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
