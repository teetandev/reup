"""Test script for Phase 07 — Scheduler.

Verifies:
- User can create job
- Node is assigned and locked
- Upload token is generated
- User limit is enforced
- File size limit is enforced
- No node available returns proper error
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db.enums import NodeStatus, UserRole, UserStatus
from app.db.models import User, VpsNode
from app.db.session import SessionLocal
from app.jobs.service import count_active_jobs, create_job

settings = get_settings()


def test_scheduler():
    """Test scheduler job creation and node assignment."""
    db = SessionLocal()

    try:
        # 1. Create test user
        user = User(
            display_name="Test User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            max_file_mb=500,
            max_concurrent_jobs=2,
            daily_job_limit=10,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✓ Created test user: {user.id}")

        # 2. Create test node
        node = VpsNode(
            name="test-node-1",
            public_url="https://test-node-1.example.com",
            status=NodeStatus.IDLE,
            enabled=True,
            last_heartbeat_at=db.execute("SELECT now()").scalar(),
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        print(f"✓ Created test node: {node.id}")

        # 3. Test job creation
        job1, token1 = create_job(
            db=db,
            settings=settings,
            user=user,
            api_key_id=None,
            original_filename="test-video.mp4",
            file_size_bytes=100_000_000,  # 100MB
        )
        print(f"✓ Created job 1: {job1.id}")
        print(f"  Status: {job1.status.value}")
        print(f"  Node: {job1.node_id}")
        print(f"  Upload URL: {job1.node_upload_url}")
        print(f"  Token length: {len(token1)}")

        # 4. Verify node is locked
        db.refresh(node)
        assert node.status == NodeStatus.BUSY, f"Expected BUSY, got {node.status}"
        assert node.current_job_id == job1.id, "Node should have current_job_id set"
        print(f"✓ Node is locked (BUSY, current_job_id={node.current_job_id})")

        # 5. Test active job count
        active_count = count_active_jobs(db, user.id)
        assert active_count == 1, f"Expected 1 active job, got {active_count}"
        print(f"✓ Active job count: {active_count}")

        # 6. Test file size limit
        try:
            create_job(
                db=db,
                settings=settings,
                user=user,
                api_key_id=None,
                original_filename="large-video.mp4",
                file_size_bytes=600_000_000,  # 600MB > 500MB limit
            )
            print("✗ Should have rejected large file")
            sys.exit(1)
        except Exception as e:
            if "FILE_TOO_LARGE" in str(e):
                print(f"✓ File size limit enforced: {e}")
            else:
                raise

        # 7. Test no node available (only one node, already busy)
        try:
            create_job(
                db=db,
                settings=settings,
                user=user,
                api_key_id=None,
                original_filename="test-video-2.mp4",
                file_size_bytes=50_000_000,
            )
            print("✗ Should have returned NO_NODE_AVAILABLE")
            sys.exit(1)
        except Exception as e:
            if "NO_NODE_AVAILABLE" in str(e):
                print(f"✓ No node available error: {e}")
            else:
                raise

        # 8. Add second node and create second job
        node2 = VpsNode(
            name="test-node-2",
            public_url="https://test-node-2.example.com",
            status=NodeStatus.IDLE,
            enabled=True,
            last_heartbeat_at=db.execute("SELECT now()").scalar(),
        )
        db.add(node2)
        db.commit()
        db.refresh(node2)
        print(f"✓ Created second node: {node2.id}")

        job2, token2 = create_job(
            db=db,
            settings=settings,
            user=user,
            api_key_id=None,
            original_filename="test-video-2.mp4",
            file_size_bytes=50_000_000,
        )
        print(f"✓ Created job 2: {job2.id}")

        # 9. Verify second node is locked
        db.refresh(node2)
        assert node2.status == NodeStatus.BUSY, f"Expected BUSY, got {node2.status}"
        assert node2.current_job_id == job2.id, "Node 2 should have current_job_id set"
        print(f"✓ Node 2 is locked (BUSY, current_job_id={node2.current_job_id})")

        # 10. Test user limit (max_concurrent_jobs=2, already have 2 active)
        active_count = count_active_jobs(db, user.id)
        assert active_count == 2, f"Expected 2 active jobs, got {active_count}"
        print(f"✓ Active job count: {active_count}")

        # Add third node for testing user limit
        node3 = VpsNode(
            name="test-node-3",
            public_url="https://test-node-3.example.com",
            status=NodeStatus.IDLE,
            enabled=True,
            last_heartbeat_at=db.execute("SELECT now()").scalar(),
        )
        db.add(node3)
        db.commit()

        try:
            create_job(
                db=db,
                settings=settings,
                user=user,
                api_key_id=None,
                original_filename="test-video-3.mp4",
                file_size_bytes=50_000_000,
            )
            print("✗ Should have returned USER_LIMIT_REACHED")
            sys.exit(1)
        except Exception as e:
            if "USER_LIMIT_REACHED" in str(e):
                print(f"✓ User limit enforced: {e}")
            else:
                raise

        print("\n✅ All scheduler tests passed!")

    finally:
        # Cleanup
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_scheduler()
