"""initial schema — users, api_keys, vps_nodes, jobs, job_events, admin_audit_logs

Matches docs/specs/DATABASE_SCHEMA.md.

Revision ID: 0001
Revises:
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Enum types (created explicitly; columns reference them with create_type=False).
user_status = postgresql.ENUM("ACTIVE", "BLOCKED", name="user_status", create_type=False)
user_role = postgresql.ENUM("USER", "ADMIN", name="user_role", create_type=False)
api_key_status = postgresql.ENUM("ACTIVE", "REVOKED", name="api_key_status", create_type=False)
node_status = postgresql.ENUM(
    "PROVISIONING", "IDLE", "BUSY", "OFFLINE", "DISABLED", "ERROR",
    name="node_status", create_type=False,
)
job_status = postgresql.ENUM(
    "CREATED", "ASSIGNED_NODE", "WAITING_UPLOAD", "UPLOADING", "UPLOADED",
    "EXTRACTING_AUDIO", "CHUNKING_AUDIO", "TRANSCRIBING", "TRANSLATING",
    "GENERATING_SRT", "RENDERING", "DONE", "FAILED", "CANCELLED", "EXPIRED",
    name="job_status", create_type=False,
)

_ALL_ENUMS = (user_status, user_role, api_key_status, node_status, job_status)


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in _ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("role", user_role, server_default=sa.text("'USER'"), nullable=False),
        sa.Column("status", user_status, server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("max_file_mb", sa.Integer(), server_default=sa.text("500"), nullable=False),
        sa.Column("max_concurrent_jobs", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("daily_job_limit", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "api_keys",
        _uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_prefix", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("status", api_key_status, server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"])

    op.create_table(
        "vps_nodes",
        _uuid_pk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=False),
        sa.Column("status", node_status, server_default=sa.text("'PROVISIONING'"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("max_jobs", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("current_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_token_prefix", sa.Text(), nullable=True),
        sa.Column("node_token_hash", sa.Text(), nullable=True),
        sa.Column("agent_version", sa.Text(), nullable=True),
        sa.Column("cpu_percent", sa.Numeric(), nullable=True),
        sa.Column("ram_used_mb", sa.Integer(), nullable=True),
        sa.Column("ram_total_mb", sa.Integer(), nullable=True),
        sa.Column("disk_free_gb", sa.Numeric(), nullable=True),
        sa.Column("last_heartbeat_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_url"),
    )
    op.create_index("idx_vps_nodes_status", "vps_nodes", ["status"])
    op.create_index("idx_vps_nodes_enabled", "vps_nodes", ["enabled"])
    op.create_index("idx_vps_nodes_last_heartbeat", "vps_nodes", ["last_heartbeat_at"])

    op.create_table(
        "jobs",
        _uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", job_status, server_default=sa.text("'CREATED'"), nullable=False),
        sa.Column("current_step", sa.Text(), nullable=True),
        sa.Column("progress_percent", sa.Numeric(), server_default=sa.text("0"), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("upload_token_hash", sa.Text(), nullable=True),
        sa.Column("upload_token_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("node_upload_url", sa.Text(), nullable=True),
        sa.Column("node_download_url", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("upload_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("upload_completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("processing_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["vps_nodes.id"]),
    )
    op.create_index("idx_jobs_user_id", "jobs", ["user_id"])
    op.create_index("idx_jobs_node_id", "jobs", ["node_id"])
    op.create_index("idx_jobs_status", "jobs", ["status"])
    op.create_index("idx_jobs_created_at", "jobs", ["created_at"])

    op.create_table(
        "job_events",
        _uuid_pk(),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["vps_nodes.id"]),
    )
    op.create_index("idx_job_events_job_id", "job_events", ["job_id"])
    op.create_index("idx_job_events_created_at", "job_events", ["created_at"])

    op.create_table(
        "admin_audit_logs",
        _uuid_pk(),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_logs")
    op.drop_table("job_events")
    op.drop_table("jobs")
    op.drop_table("vps_nodes")
    op.drop_table("api_keys")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in reversed(_ALL_ENUMS):
        enum_type.drop(bind, checkfirst=True)
