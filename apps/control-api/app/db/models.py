"""SQLAlchemy ORM models — must match docs/specs/DATABASE_SCHEMA.md.

Tables: users, api_keys, vps_nodes, jobs, job_events, admin_audit_logs.
Phase 03: schema only. No business logic.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import ApiKeyStatus, JobStatus, NodeStatus, UserRole, UserStatus


def _enum(py_enum: type, name: str) -> SAEnum:
    """Native PostgreSQL enum that stores the enum *values* (not member names)."""
    return SAEnum(
        py_enum,
        name=name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )


user_role_enum = _enum(UserRole, "user_role")
user_status_enum = _enum(UserStatus, "user_status")
api_key_status_enum = _enum(ApiKeyStatus, "api_key_status")
node_status_enum = _enum(NodeStatus, "node_status")
job_status_enum = _enum(JobStatus, "job_status")

_PK = lambda: mapped_column(  # noqa: E731
    UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
)
_NOW = lambda nullable=False: mapped_column(  # noqa: E731
    TIMESTAMP(timezone=True), nullable=nullable, server_default=text("now()")
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _PK()
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, server_default=text("'USER'")
    )
    status: Mapped[UserStatus] = mapped_column(
        user_status_enum, nullable=False, server_default=text("'ACTIVE'")
    )

    max_file_mb: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("500"))
    max_concurrent_jobs: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    daily_job_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("10"))

    created_at: Mapped[datetime.datetime] = _NOW()
    updated_at: Mapped[datetime.datetime] = _NOW()

    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user", cascade="all, delete-orphan")
    jobs: Mapped[list[Job]] = relationship(back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("idx_api_keys_user_id", "user_id"),
        Index("idx_api_keys_prefix", "key_prefix"),
    )

    id: Mapped[uuid.UUID] = _PK()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    key_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[ApiKeyStatus] = mapped_column(
        api_key_status_enum, nullable=False, server_default=text("'ACTIVE'")
    )

    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = _NOW()
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="api_keys")


class VpsNode(Base):
    __tablename__ = "vps_nodes"
    __table_args__ = (
        Index("idx_vps_nodes_status", "status"),
        Index("idx_vps_nodes_enabled", "enabled"),
        Index("idx_vps_nodes_last_heartbeat", "last_heartbeat_at"),
    )

    id: Mapped[uuid.UUID] = _PK()

    name: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    status: Mapped[NodeStatus] = mapped_column(
        node_status_enum, nullable=False, server_default=text("'PROVISIONING'")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    max_jobs: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    # No FK on purpose (avoids a cycle with jobs.node_id); see DATABASE_SCHEMA.md.
    current_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    node_token_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpu_percent: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    ram_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_free_gb: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    last_heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime.datetime] = _NOW()
    updated_at: Mapped[datetime.datetime] = _NOW()


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_jobs_user_id", "user_id"),
        Index("idx_jobs_node_id", "node_id"),
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = _PK()

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vps_nodes.id"), nullable=True
    )

    status: Mapped[JobStatus] = mapped_column(
        job_status_enum, nullable=False, server_default=text("'CREATED'")
    )
    current_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[float] = mapped_column(
        Numeric, nullable=False, server_default=text("0")
    )

    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    upload_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    upload_token_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    node_upload_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_download_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = _NOW()
    assigned_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    upload_started_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    upload_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    processing_started_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime.datetime] = _NOW()

    user: Mapped[User] = relationship(back_populates="jobs")
    events: Mapped[list[JobEvent]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (
        Index("idx_job_events_job_id", "job_id"),
        Index("idx_job_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = _PK()
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vps_nodes.id"), nullable=True
    )

    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime.datetime] = _NOW()

    job: Mapped[Job] = relationship(back_populates="events")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = _PK()
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # 'metadata' is reserved on the declarative base -> map attribute to the column name.
    audit_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime.datetime] = _NOW()
