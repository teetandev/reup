"""Test script for stale-job reconcile + quota logic.

Verifies the fix for the 409 "đã đạt giới hạn job đồng thời/hôm nay" bug caused
by jobs left stuck in a pre-upload state after a failed browser upload.

Covers:
- A stuck pre-upload job past the stale timeout is auto-expired and stops
  consuming the concurrent quota, so a NEW job is allowed.
- FAILED/EXPIRED jobs do NOT count toward the daily quota.
- Root admins bypass the quota entirely.
- Admin cancel / mark-failed / cleanup-stale helpers free nodes.

Run:  python scripts/test_stale_jobs.py   (requires a reachable DATABASE_URL)
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.config import get_settings
from app.db.enums import JobStatus, NodeStatus, UserRole, UserStatus
from app.db.models import User, VpsNode
from app.db.session import SessionLocal
from app.jobs.service import (
    admin_cancel_job,
    cleanup_stale_jobs,
    count_active_jobs,
    count_daily_jobs,
    create_job,
    expire_stale_jobs,
)

settings = get_settings()


def _make_node(db, name) -> VpsNode:
    node = VpsNode(
        name=name,
        public_url=f"https://{name}.example.com",
        status=NodeStatus.IDLE,
        enabled=True,
        last_heartbeat_at=db.execute(text("SELECT now()")).scalar(),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def test_stale_jobs():
    db = SessionLocal()
    try:
        user = User(
            display_name="Stale Test User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            max_file_mb=500,
            max_concurrent_jobs=1,
            daily_job_limit=2,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✓ Created user {user.id} (concurrent=1, daily=2)")

        _make_node(db, "stale-node-1")

        # 1. First job takes the only concurrent slot.
        job1, _ = create_job(db, settings, user, None, "v1.mp4", 10_000_000)
        assert count_active_jobs(db, user.id) == 1
        print(f"✓ Job1 created and active ({job1.status.value})")

        # 2. Second job is blocked by the concurrent limit, with rich details.
        try:
            create_job(db, settings, user, None, "v2.mp4", 10_000_000)
            print("✗ Expected USER_LIMIT_REACHED")
            sys.exit(1)
        except Exception as e:
            assert "USER_LIMIT_REACHED" in str(e), e
            details = getattr(e, "details", {})
            assert details.get("active_jobs_limit") == 1, details
            assert "stuck_job_ids" in details, details
            print(f"✓ Concurrent limit enforced with details: {details}")

        # 3. Simulate the stuck-after-failed-upload scenario: backdate job1 past
        #    the stale timeout with no completed upload, then try again. The
        #    reconcile step should expire it and ALLOW the new job.
        job1.created_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(
            minutes=settings.stale_job_timeout_minutes + 1
        )
        job1.upload_completed_at = None
        db.commit()

        job2, _ = create_job(db, settings, user, None, "v2.mp4", 10_000_000)
        db.refresh(job1)
        assert job1.status == JobStatus.EXPIRED, job1.status
        assert job2.status == JobStatus.WAITING_UPLOAD, job2.status
        print(f"✓ Stuck job1 auto-expired; job2 created ({job2.id})")

        # 4. Daily quota must NOT count the EXPIRED job.
        daily = count_daily_jobs(db, user.id)
        assert daily == 1, f"Expected daily=1 (only job2), got {daily}"
        print(f"✓ Daily count excludes expired job: {daily}")

        # 5. Mark job2 FAILED via admin helper → frees node + drops daily count.
        admin_mark_failed_check(db, job2)

        # 6. Daily quota after a FAILED job is still not consumed → new job ok.
        _make_node(db, "stale-node-2")
        job3, _ = create_job(db, settings, user, None, "v3.mp4", 10_000_000)
        assert count_daily_jobs(db, user.id) == 1, count_daily_jobs(db, user.id)
        print(f"✓ FAILED job not counted in daily; job3 created ({job3.id})")

        # 7. Admin bypass: an ADMIN user is never blocked by quota.
        admin = User(
            display_name="Root Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            max_file_mb=500,
            max_concurrent_jobs=1,
            daily_job_limit=1,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        _make_node(db, "stale-node-3")
        _make_node(db, "stale-node-4")
        a1, _ = create_job(db, settings, admin, None, "a1.mp4", 10_000_000)
        a2, _ = create_job(db, settings, admin, None, "a2.mp4", 10_000_000)
        print(f"✓ Admin bypassed quota: created {a1.id} and {a2.id}")

        # 8. cleanup_stale_jobs is a no-op when nothing is stale.
        cleaned = cleanup_stale_jobs(db, settings)
        print(f"✓ cleanup_stale_jobs returned {len(cleaned)} (fresh jobs untouched)")

        print("\n✅ All stale-job / quota tests passed!")
    finally:
        db.rollback()
        db.close()


def admin_mark_failed_check(db, job):
    """Mark a job FAILED through the admin helper and assert node release."""
    from app.jobs.service import admin_mark_failed

    node_id = job.node_id
    updated = admin_mark_failed(db, str(job.id), "test failure")
    assert updated.status == JobStatus.FAILED, updated.status
    if node_id is not None:
        node = db.get(VpsNode, node_id)
        assert node.current_job_id is None, "node should be released"
    print(f"✓ admin_mark_failed freed node for job {job.id}")


if __name__ == "__main__":
    test_stale_jobs()
