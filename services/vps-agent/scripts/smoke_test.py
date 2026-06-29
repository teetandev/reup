"""Phase 05 smoke test for the VPS Agent (no external services needed).

Verifies: app boots, /health and /status shape, single-job guard (NODE_BUSY),
and the structured error envelope. Run from services/vps-agent::

    python scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make `app` importable when run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Configure a throwaway env before importing the app.
os.environ.setdefault("NODE_ID", "test-node-1")
os.environ.setdefault("NODE_TOKEN", "secret-not-logged")
os.environ["WORK_DIR"] = tempfile.mkdtemp(prefix="reup-agent-test-")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.state import get_node_state  # noqa: E402

client = TestClient(app)
failures: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}{(' — ' + extra) if extra else ''}")
    if not ok:
        failures.append(name)


# /health
r = client.get("/health")
body = r.json()
check("/health 200", r.status_code == 200, str(r.status_code))
check(
    "/health shape",
    body.get("ok") is True
    and body.get("node_id") == "test-node-1"
    and body.get("status") == "IDLE"
    and body.get("current_job_id") is None,
    str(body),
)

# /status
r = client.get("/status")
body = r.json()
res = body.get("resource", {})
check("/status 200", r.status_code == 200, str(r.status_code))
check(
    "/status resource keys",
    {"cpu_percent", "ram_used_mb", "ram_total_mb", "disk_free_gb"} <= set(res),
    str(res),
)

# Single-job guard: acquire, then second acquire must raise NODE_BUSY.
state = get_node_state()
state.acquire_job("job-A")
snap = state.snapshot()
check("acquire sets BUSY", snap.status == "BUSY" and snap.current_job_id == "job-A")

# /health reflects BUSY + current job.
body = client.get("/health").json()
check("/health reflects job", body["status"] == "BUSY" and body["current_job_id"] == "job-A")

try:
    state.acquire_job("job-B")
    check("second acquire rejected", False, "no error raised")
except Exception as exc:  # AgentError
    code = getattr(exc, "code", None)
    check("second acquire -> NODE_BUSY", code == "NODE_BUSY", str(code))

# Release returns to IDLE.
state.release_job("job-A")
check("release returns IDLE", state.snapshot().status == "IDLE")

# Unknown route -> structured 404 envelope.
r = client.get("/does-not-exist")
body = r.json()
check(
    "404 structured error",
    r.status_code == 404 and body.get("error", {}).get("code") == "NOT_FOUND",
    str(body),
)

print()
if failures:
    print(f"{len(failures)} check(s) FAILED: {failures}")
    sys.exit(1)
print("All smoke checks passed.")
