"""Phase 10 smoke test for the VPS Agent job/pipeline endpoints.

Exercises the HTTP surface of start/status/download/cancel **without** running the
real video pipeline (no ffmpeg, no Groq/Gemini keys, no Control API): the pipeline
launcher and the Control-API callback are monkeypatched. Auth uses the node token
path so no Control API round-trip is needed.

Run from services/vps-agent::

    python scripts/test_phase10.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NODE_TOKEN = "node_live_test_token"
os.environ.setdefault("NODE_ID", "test-node-1")
os.environ["NODE_TOKEN"] = NODE_TOKEN
os.environ["WORK_DIR"] = tempfile.mkdtemp(prefix="reup-agent-p10-")

from fastapi.testclient import TestClient  # noqa: E402

from app import pipeline_runner  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.job_runtime import get_job_registry  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import jobs as jobs_router  # noqa: E402
from app.state import get_node_state  # noqa: E402

client = TestClient(app)
settings = get_settings()
registry = get_job_registry()
failures: list[str] = []
AUTH = {"Authorization": f"Bearer {NODE_TOKEN}"}


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + extra) if extra else ''}")
    if not ok:
        failures.append(name)


# --- Fakes: do not run the real pipeline ------------------------------------------
def fake_start_pipeline_thread(job_id: str, _settings) -> None:
    """Pretend the worker started and is mid-render."""
    registry.update(job_id, status="RENDERING", progress_percent=70.0, current_step="RENDERING")


async def fake_notify(*_args, **_kwargs) -> None:
    return None


jobs_router.start_pipeline_thread = fake_start_pipeline_thread
jobs_router.notify_control_status = fake_notify


def job_dir(job_id: str) -> Path:
    return Path(settings.work_dir) / "jobs" / job_id


def write_input(job_id: str) -> None:
    d = job_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.mp4").write_bytes(b"fake-mp4-bytes")


def write_output(job_id: str) -> None:
    out = job_dir(job_id) / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "output.mp4").write_bytes(b"fake-rendered-mp4")


# 1. start with no input -> 404 INPUT_NOT_FOUND
jid_missing = str(uuid.uuid4())
r = client.post(f"/jobs/{jid_missing}/start", headers=AUTH)
check("start missing input -> 404 INPUT_NOT_FOUND",
      r.status_code == 404 and r.json()["error"]["code"] == "INPUT_NOT_FOUND", str(r.json()))

# 2. start without auth -> 401
jid = str(uuid.uuid4())
write_input(jid)
r = client.post(f"/jobs/{jid}/start")
check("start without auth -> 401", r.status_code == 401, str(r.status_code))

# 3. start with input + auth -> 200 STARTED, slot acquired
r = client.post(f"/jobs/{jid}/start", headers=AUTH)
check("start -> 200 STARTED", r.status_code == 200 and r.json()["status"] == "STARTED", str(r.json()))
check("node slot acquired", get_node_state().snapshot().current_job_id == jid)

# 4. status reflects running record
r = client.get(f"/jobs/{jid}/status")
body = r.json()
check("status -> RENDERING 70%",
      r.status_code == 200 and body["status"] == "RENDERING" and body["progress_percent"] == 70.0,
      str(body))

# 5. download before DONE -> 409 INVALID_JOB_STATUS
r = client.get(f"/jobs/{jid}/download")
check("download while running -> 409",
      r.status_code == 409 and r.json()["error"]["code"] == "INVALID_JOB_STATUS", str(r.json()))

# 6. second job while busy -> 409 NODE_BUSY
jid2 = str(uuid.uuid4())
write_input(jid2)
r = client.post(f"/jobs/{jid2}/start", headers=AUTH)
check("second job while busy -> 409 NODE_BUSY",
      r.status_code == 409 and r.json()["error"]["code"] == "NODE_BUSY", str(r.json()))

# 7. simulate completion -> download serves MP4
registry.update(jid, status="DONE", progress_percent=100.0, current_step="DONE")
write_output(jid)
r = client.get(f"/jobs/{jid}/download")
check("download when DONE -> 200 mp4",
      r.status_code == 200 and r.headers.get("content-type") == "video/mp4", str(r.status_code))

# 8. invalid (non-uuid) job id -> 404 JOB_NOT_FOUND
r = client.get("/jobs/not-a-uuid/status")
check("non-uuid job -> 404 JOB_NOT_FOUND",
      r.status_code == 404 and r.json()["error"]["code"] == "JOB_NOT_FOUND", str(r.json()))

# 9. status of unknown job -> 404
r = client.get(f"/jobs/{uuid.uuid4()}/status")
check("unknown job status -> 404", r.status_code == 404, str(r.status_code))

# 10. cancel a not-yet-started job -> 200 CANCELLED + slot released
get_node_state().release_job(jid)  # free the slot from the completed job
jid3 = str(uuid.uuid4())
write_input(jid3)
r = client.post(f"/jobs/{jid3}/cancel", headers=AUTH)
check("cancel before start -> 200 CANCELLED",
      r.status_code == 200 and r.json()["status"] == "CANCELLED", str(r.json()))

# 11. cancel a running job -> 202 CANCELLING + flag set
jid4 = str(uuid.uuid4())
write_input(jid4)
client.post(f"/jobs/{jid4}/start", headers=AUTH)
r = client.post(f"/jobs/{jid4}/cancel", headers=AUTH)
check("cancel running -> 202 CANCELLING",
      r.status_code == 202 and registry.is_cancel_requested(jid4), str(r.json()))

# 12. progress->status mapping sanity
mp = pipeline_runner.map_progress_to_status
check("progress map 5->EXTRACTING", mp(5) == "EXTRACTING_AUDIO")
check("progress map 10->CHUNKING", mp(10) == "CHUNKING_AUDIO")
check("progress map 15->TRANSCRIBING", mp(15) == "TRANSCRIBING")
check("progress map 45->TRANSLATING", mp(45) == "TRANSLATING")
check("progress map 65->GENERATING_SRT", mp(65) == "GENERATING_SRT")
check("progress map 70->RENDERING", mp(70) == "RENDERING")
check("progress map 100->DONE", mp(100) == "DONE")

print()
if failures:
    print(f"{len(failures)} check(s) FAILED: {failures}")
    sys.exit(1)
print("All Phase 10 smoke checks passed.")
