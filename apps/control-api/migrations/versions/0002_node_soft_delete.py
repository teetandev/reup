"""node soft-delete + ON DELETE SET NULL for node foreign keys

Adds ``vps_nodes.deleted_at`` (soft-delete marker) and makes the node foreign
keys self-healing so a node row can never cause a FK violation:

- ``jobs.node_id``        -> ON DELETE SET NULL
- ``job_events.node_id``  -> ON DELETE SET NULL

Soft-delete is the primary mechanism (job history is preserved); the ON DELETE
SET NULL rules are a defensive belt-and-braces for any future hard delete and to
stop the historical 500 (FK violation on ``job_events.node_id``).

Works on PostgreSQL (Render) and is a no-op-safe on SQLite (local/dev), where
named FK drops are skipped because SQLite cannot ALTER constraints in place.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-30
"""

from alembic import context, op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _is_postgres(bind) -> bool:
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Soft-delete column (works on every dialect).
    op.add_column(
        "vps_nodes",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("idx_vps_nodes_deleted_at", "vps_nodes", ["deleted_at"])

    # 2. Make node foreign keys ON DELETE SET NULL so a node delete can never
    #    raise a FK violation (defensive — the app uses soft-delete). PostgreSQL
    #    only: SQLite cannot ALTER constraints in place, and the soft-delete path
    #    means we never hard-delete a referenced node there anyway.
    if not _is_postgres(bind) and bind is not None:
        return

    for table, column in (("jobs", "node_id"), ("job_events", "node_id")):
        # In online mode, look up the real constraint name(s); in offline (--sql)
        # mode fall back to PostgreSQL's deterministic auto-name "<t>_<c>_fkey".
        conames: list[str] = []
        if bind is not None and not context.is_offline_mode():
            rows = bind.execute(
                sa.text(
                    """
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_attribute att
                      ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
                    WHERE con.contype = 'f'
                      AND rel.relname = :table
                      AND att.attname = :column
                    """
                ),
                {"table": table, "column": column},
            ).fetchall()
            conames = [r[0] for r in rows]
        if not conames:
            conames = [f"{table}_{column}_fkey"]

        for conname in conames:
            op.drop_constraint(conname, table, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{table}_node_id_vps_nodes",
            table,
            "vps_nodes",
            [column],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _is_postgres(bind):
        for table, column in (("jobs", "node_id"), ("job_events", "node_id")):
            op.drop_constraint(f"fk_{table}_node_id_vps_nodes", table, type_="foreignkey")
            op.create_foreign_key(
                None, table, "vps_nodes", [column], ["id"]
            )

    op.drop_index("idx_vps_nodes_deleted_at", table_name="vps_nodes")
    op.drop_column("vps_nodes", "deleted_at")
