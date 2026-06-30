"""VPS node registry + heartbeat request/response schemas (Phase 06)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

# Statuses a VPS agent is allowed to self-report via heartbeat. Lifecycle-only
# statuses (PROVISIONING/OFFLINE/DISABLED) are set by the control plane, not the
# agent, so they are deliberately excluded here.
HeartbeatStatus = str  # validated against this set in the service layer
AGENT_REPORTABLE_STATUSES = {"IDLE", "BUSY", "ERROR"}


class RegisterNodeRequest(BaseModel):
    """Admin payload to register a new VPS node."""

    name: str = Field(min_length=1)
    public_url: str = Field(min_length=1)


class RegisterNodeResponse(BaseModel):
    """Returned once at registration.

    ``node_token`` is the plaintext token — it is shown **once** here and never
    retrievable again. The ``install_command`` embeds it for the admin to paste
    onto the VPS. Only ``node_token_hash`` + ``node_token_prefix`` are persisted.
    """

    id: str
    name: str
    public_url: str
    status: str
    node_token: str
    node_token_prefix: str
    install_command: str


class NodeResponse(BaseModel):
    """Admin-facing node view. Never includes the token hash or any secret."""

    id: str
    name: str
    public_url: str
    status: str
    enabled: bool
    max_jobs: int
    current_job_id: str | None
    node_token_prefix: str | None
    agent_version: str | None
    cpu_percent: float | None
    ram_used_mb: int | None
    ram_total_mb: int | None
    disk_free_gb: float | None
    last_heartbeat_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


class RotateNodeTokenResponse(BaseModel):
    """Returned once when an admin rotates a node's token.

    ``node_token`` is the new plaintext token, shown **once**. The previous token
    is invalidated immediately.
    """

    id: str
    name: str
    node_token: str
    node_token_prefix: str


class NodeActionResponse(BaseModel):
    """Generic ack for enable/disable/delete node admin actions."""

    id: str
    status: str
    enabled: bool
    message: str


class NodeDebugResponse(BaseModel):
    """Non-secret assignability diagnostics for a single node."""

    node_id: str
    name: str
    enabled: bool
    status: str
    current_job_id: str | None
    last_heartbeat_at: str | None
    heartbeat_age_seconds: int | None
    stale_threshold_seconds: int
    assignable: bool
    reasons: list[str]


class HeartbeatRequest(BaseModel):
    """Heartbeat payload sent by a VPS agent (node-authenticated)."""

    node_id: str
    status: str
    current_job_id: str | None = None
    cpu_percent: float | None = Field(default=None, ge=0)
    ram_used_mb: int | None = Field(default=None, ge=0)
    ram_total_mb: int | None = Field(default=None, ge=0)
    disk_free_gb: float | None = Field(default=None, ge=0)
    agent_version: str | None = None


class HeartbeatResponse(BaseModel):
    """Acknowledges a heartbeat and echoes the stored (effective) status."""

    ok: bool
    node_id: str
    status: str
