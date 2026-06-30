"""Regression test for the node-delete 500 (soft-delete behaviour).

Reproduces the original bug (DELETE /admin/nodes/{id} -> 500 because a node was
referenced by jobs *and* job_events) and verifies the soft-delete fix:

  1. Create a node.
  2. Create a job + job_event referencing that node.
  3. Soft-delete the node -> no exception (was a FK violation / 500).
  4. Job + job_event history is preserved.
  5. The node is hidden from list_nodes and from get_node (NODE_NOT_FOUND).
  6. The scheduler never assigns the deleted node (assign_idle_node -> None).
  7. A BUSY node is refused without force, allowed with force.

Runs on a throwaway SQLite database so it needs no Postgres/Render.
"""

from __future__ import annotations

import datetime as dt
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlalchemy as sa
from sqlalchemy import create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker

# --- Make Postgres-specific column types renderable on SQLite (test only) ---
# Production runs on Postgres; these shims only affect this throwaway DB so we
# can exercise the real ORM models without a Postgres server.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "CHAR(36)"


from app.config import Settings
from app.db.base import Base
from app.db.enums import JobStatus, NodeStatus, UserRole, UserStatus
from app.db.models import Job, JobEvent, User, VpsNode
from app.errors import ApiError
from app.jobs.service import assign_idle_node
from app.nodes import service as node_service


def _make_session():
    """In-memory SQLite with FK enforcement on (so we'd catch a real FK bug)."""
    engine = create_engine("sqlite://", future=True)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
        # Provide a now() function so server_default=text("now()") works.
        dbapi_conn.create_function(
            "now", 0, lambda: dt.datetime.now(dt.timezone.utc).isoformat(sep=" ")
        )
        dbapi_conn.create_function(
            "gen_random_uuid", 0, lambda: str(uuid.uuid4())
        )

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def main() -> None:
    db = _make_session()
    settings = Settings(node_heartbeat_stale_seconds=60)

    # 1. user + node + job + job_event (ids set explicitly: SQLite has no
    #    gen_random_uuid() server default)
    user = User(id=uuid.uuid4(), display_name="T", role=UserRole.USER, status=UserStatus.ACTIVE)
    db.add(user)
    db.flush()

    node = VpsNode(
        id=uuid.uuid4(),
        name="codespace-worker-01",
        public_url="https://redesigned-space-memory-xxxx-8100.app.github.dev",
        status=NodeStatus.IDLE,
        enabled=True,
        last_heartbeat_at=_now(),
        node_token_prefix="abc",
        node_token_hash="hash",
    )
    db.add(node)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        user_id=user.id,
        node_id=node.id,
        status=JobStatus.DONE,
        original_filename="video.mp4",
        progress_percent=0,
    )
    db.add(job)
    db.flush()

    event_row = JobEvent(id=uuid.uuid4(), job_id=job.id, node_id=node.id, event_type="JOB_CREATED")
    db.add(event_row)
    db.commit()

    node_id = node.id
    job_id = job.id
    event_id = event_row.id
    print(f"✓ Setup: node={node_id} job={job_id} event={event_id}")

    # 2. assignable before delete
    assert assign_idle_node(db, settings) is not None, "node should be assignable pre-delete"
    print("✓ Node is assignable before delete")

    # 3. DELETE — must not raise (the old hard-delete raised FK violation -> 500)
    try:
        node_service.delete_node(db, node, force=False)
    except ApiError as exc:
        print(f"✗ delete_node raised ApiError {exc.status_code} {exc.code}: {exc.message}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ delete_node raised {type(exc).__name__}: {exc}  (this WAS the 500)")
        sys.exit(1)
    print("✓ delete_node succeeded with NO exception (no 500)")

    # 4. history preserved
    db.expire_all()
    assert db.get(Job, job_id) is not None, "job history must be preserved"
    assert db.get(JobEvent, event_id) is not None, "job_event history must be preserved"
    kept_node = db.get(VpsNode, node_id)
    assert kept_node is not None and kept_node.deleted_at is not None, "node row kept + marked deleted"
    assert kept_node.enabled is False and kept_node.status == NodeStatus.DISABLED
    assert kept_node.node_token_hash is None, "token must be wiped"
    assert kept_node.current_job_id is None, "current_job_id must be cleared"
    assert "#deleted-" in kept_node.public_url, "public_url should be freed"
    print("✓ Job + job_event preserved; node soft-deleted, token wiped, url freed")

    # 5. hidden from list + get_node
    assert all(n.id != node_id for n in node_service.list_nodes(db, 60)), "deleted node hidden from list"
    try:
        node_service.get_node(db, str(node_id), 60)
        print("✗ get_node returned a deleted node")
        sys.exit(1)
    except ApiError as exc:
        assert exc.status_code == 404 and exc.code == "NODE_NOT_FOUND"
    print("✓ Deleted node hidden from list_nodes and get_node -> 404")

    # 6. scheduler never picks the deleted node
    assert assign_idle_node(db, settings) is None, "deleted node must NOT be assignable"
    print("✓ Scheduler does not assign the deleted node")

    # 7. the same public_url can be reused by a fresh node
    fresh, _tok = node_service.register_node(
        db, settings, "codespace-worker-02",
        "https://redesigned-space-memory-xxxx-8100.app.github.dev",
    )
    assert fresh.id != node_id
    print("✓ Original public_url reusable by a new node")

    # 8. BUSY node refused without force, allowed with force
    busy = VpsNode(
        id=uuid.uuid4(), name="busy", public_url="https://busy.example.com",
        status=NodeStatus.BUSY, enabled=True, last_heartbeat_at=_now(),
    )
    db.add(busy)
    db.commit()
    try:
        node_service.delete_node(db, busy, force=False)
        print("✗ BUSY node deleted without force")
        sys.exit(1)
    except ApiError as exc:
        assert exc.status_code == 409 and exc.code == "NODE_BUSY"
    node_service.delete_node(db, busy, force=True)
    db.expire_all()
    assert db.get(VpsNode, busy.id).deleted_at is not None
    print("✓ BUSY node refused without force, deleted with force")

    print("\n✅ All node-delete tests passed!")
    db.close()


if __name__ == "__main__":
    main()
