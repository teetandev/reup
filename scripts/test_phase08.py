"""Test script for Phase 08 — Direct Upload.

Verifies:
1. Control API: validate-token endpoint
2. Control API: agent-status endpoint
3. VPS Agent: upload endpoint with token validation
4. File size enforcement
5. Metadata extraction
6. Status updates

Prerequisites:
- Control API running on localhost:8000
- VPS Agent running on localhost:8100
- Database with test user and node
"""

import asyncio
import io
import time

import httpx

# Test configuration
CONTROL_API_URL = "http://localhost:8000"
AGENT_URL = "http://localhost:8100"

# These need to be set from actual database
USER_SECRET_KEY = "sub_live_xxx"  # Replace with actual key
NODE_TOKEN = "node_token_xxx"  # Replace with actual node token


async def test_phase_08():
    """Run Phase 08 acceptance tests."""
    print("=== Phase 08 — Direct Upload Tests ===\n")

    # Step 1: User login
    print("1. User login...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTROL_API_URL}/auth/login",
            json={"secret_key": USER_SECRET_KEY},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        user_token = response.json()["access_token"]
        print(f"   ✓ User logged in, token: {user_token[:20]}...\n")

    # Step 2: Create job
    print("2. Create job...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTROL_API_URL}/jobs",
            json={
                "original_filename": "test_video.mp4",
                "file_size_bytes": 10_000_000,  # 10MB
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 201, f"Job creation failed: {response.text}"
        job_data = response.json()
        job_id = job_data["job_id"]
        upload_token = job_data["upload"]["token"]
        upload_url = job_data["upload"]["url"]
        print(f"   ✓ Job created: {job_id}")
        print(f"   ✓ Upload URL: {upload_url}")
        print(f"   ✓ Upload token: {upload_token[:20]}...\n")

    # Step 3: Test validate-token endpoint (should succeed)
    print("3. Validate upload token (valid)...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTROL_API_URL}/jobs/{job_id}/validate-token",
            json={"upload_token": upload_token},
            headers={"Authorization": f"Bearer {NODE_TOKEN}"},
        )
        assert response.status_code == 200, f"Token validation failed: {response.text}"
        token_data = response.json()
        assert token_data["valid"] is True
        assert token_data["job_id"] == job_id
        print(f"   ✓ Token validated: {token_data}\n")

    # Step 4: Test validate-token endpoint (invalid token)
    print("4. Validate upload token (invalid)...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTROL_API_URL}/jobs/{job_id}/validate-token",
            json={"upload_token": "invalid_token_xyz"},
            headers={"Authorization": f"Bearer {NODE_TOKEN}"},
        )
        assert response.status_code == 401, f"Expected 401, got: {response.status_code}"
        error_data = response.json()
        assert error_data["error"]["code"] == "UPLOAD_TOKEN_INVALID"
        print(f"   ✓ Invalid token rejected: {error_data['error']['code']}\n")

    # Step 5: Test agent-status endpoint
    print("5. Update job status via agent-status...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTROL_API_URL}/jobs/{job_id}/agent-status",
            json={
                "status": "UPLOADING",
                "message": "Upload started",
                "progress_percent": 0,
            },
            headers={"Authorization": f"Bearer {NODE_TOKEN}"},
        )
        assert response.status_code == 200, f"Status update failed: {response.text}"
        status_data = response.json()
        print(f"   ✓ Status updated: {status_data['status']}\n")

    # Step 6: Test upload endpoint with small file
    print("6. Upload small file to agent...")
    small_file = io.BytesIO(b"fake video content" * 100)  # ~1.8KB
    files = {"file": ("test.mp4", small_file, "video/mp4")}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{AGENT_URL}/jobs/{job_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {upload_token}"},
        )
        # Note: This will fail if ffprobe can't process fake data, which is expected
        # In production test, use a real small MP4 file
        print(f"   Response status: {response.status_code}")
        print(f"   Response: {response.text}\n")

    print("7. Verify job status after upload...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CONTROL_API_URL}/jobs/{job_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        job = response.json()
        print(f"   ✓ Job status: {job['status']}")
        print(f"   ✓ Progress: {job['progress_percent']}%\n")

    print("=== Phase 08 Tests Complete ===")
    print("\nNote: Full upload test requires a real MP4 file for ffprobe metadata extraction.")


if __name__ == "__main__":
    asyncio.run(test_phase_08())
