# services/vps-agent

FastAPI agent running on each Ubuntu VPS node (target 2vCPU / 2GB RAM).

Responsibilities:
- Receive the browser's direct video upload (validates upload token and 500MB limit). *(Phase 08)*
- Run the video pipeline (`packages/video-pipeline`): extract -> chunk -> transcribe -> translate -> SRT -> hardsub render. *(Phase 09–10)*
- Send heartbeat + progress to the Control API; serve the finished MP4 for download. *(Phase 06+)*

**Rules**
- `MAX_JOBS=1` — never run two jobs on one node (enforced by the single-job guard in `app/state.py`).
- Built for low resources: `FFMPEG_THREADS=1`, `FFMPEG_PRESET=ultrafast`, `FFMPEG_CRF=28`.
- Never trust user-provided paths/filenames; validate file size and type.
- Never log `NODE_TOKEN` or expose it to clients.

## Phase 05 — what exists now

Base agent only (no upload, heartbeat, or pipeline yet):

```text
app/
  config.py          env config (NODE_ID, NODE_TOKEN, CONTROL_API_URL, AGENT_PUBLIC_URL,
                     MAX_JOBS=1, MAX_FILE_MB=500, WORK_DIR, FFMPEG/FFPROBE bins)
  errors.py          AgentError + structured {"error":{code,message,details}} envelope
  logging_config.py  console logging
  resources.py       psutil CPU/RAM/disk sampling
  state.py           NodeState + single-job guard (acquire/release, MAX_JOBS=1)
  routers/health.py  GET /health, GET /status
  main.py            create_app(); creates WORK_DIR; inits node state
scripts/smoke_test.py  in-process Phase 05 verification (no external services)
```

### Endpoints

- `GET /health` → `{"ok": true, "node_id", "status", "current_job_id"}`
- `GET /status` → `{"node_id", "status", "current_job_id", "resource": {cpu_percent, ram_used_mb, ram_total_mb, disk_free_gb}}`

Both are unauthenticated probes and never expose the node token.

## Run

```powershell
cd services\vps-agent
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then fill NODE_ID / NODE_TOKEN
uvicorn app.main:app --reload --port 8100
```

Then: `curl http://localhost:8100/health` and `curl http://localhost:8100/status`.

> On Windows, the default `WORK_DIR=/var/lib/reup-agent/jobs` from `.env.example` is a Linux
> path. For local dev either unset `WORK_DIR` (defaults to `./agent_work`) or point it at a
> writable Windows path.

## Test

```powershell
cd services\vps-agent
python scripts\smoke_test.py
```

Checks `/health` + `/status` shapes, the single-job guard (`NODE_BUSY` on a second acquire),
and the structured 404 error envelope. Uses a temp `WORK_DIR`; needs no Control API or DB.

## Phase 06 — heartbeat

The agent reports its status + host resources to the Control API at
`POST {CONTROL_API_URL}/nodes/heartbeat`, authenticated with `NODE_TOKEN`
(`Authorization: Bearer <token>` — never logged).

```text
app/heartbeat.py           build_payload(); send_heartbeat_once() (sync, for the script);
                           heartbeat_loop() (async background); heartbeat_enabled()
scripts/send_heartbeat.py  send ONE heartbeat and exit (manual test)
```

Payload (matches API_CONTRACT.md):

```json
{
  "node_id": "uuid", "status": "IDLE", "current_job_id": null,
  "cpu_percent": 12.5, "ram_used_mb": 900, "ram_total_mb": 2048,
  "disk_free_gb": 18.2, "agent_version": "0.1.0"
}
```

The background loop starts automatically when `NODE_ID`, `NODE_TOKEN`, and
`CONTROL_API_URL` are set and `HEARTBEAT_INTERVAL_SECONDS > 0` (default 30s);
otherwise it logs that it is disabled. Set `HEARTBEAT_INTERVAL_SECONDS=0` to
disable the loop and rely on the manual script only.

### Manual heartbeat test

```powershell
cd services\vps-agent
# .env must have NODE_ID / NODE_TOKEN (from admin register-node) + CONTROL_API_URL
python scripts\send_heartbeat.py
```

Exits 0 if the Control API returns 2xx. The Control API must be running and its
DB reachable, and the node must already be registered (see control-api README).

## Phase 10 — pipeline integration

The agent runs `packages/video-pipeline` for one uploaded job and reports progress.

```text
app/pipeline_runner.py   runs run_pipeline() in a daemon thread; maps progress->job
                         status; posts agent-status callbacks; releases the job slot
app/job_runtime.py       in-memory per-job status/progress registry (one job at a time)
app/routers/jobs.py      POST /jobs/{id}/start, GET /jobs/{id}/status,
                         GET /jobs/{id}/download, POST /jobs/{id}/cancel
scripts/test_phase10.py  in-process smoke test (pipeline + callbacks mocked)
```

Flow: upload (Phase 08, holds the single-job slot) → `POST /jobs/{id}/start` validates
`input.mp4` exists and spawns the pipeline thread → the thread walks
`EXTRACTING_AUDIO → CHUNKING_AUDIO → TRANSCRIBING → TRANSLATING → GENERATING_SRT →
RENDERING → DONE`, posting each transition to the Control API
(`POST {CONTROL_API_URL}/jobs/{id}/agent-status`, `Authorization: Bearer <NODE_TOKEN>`).
On `DONE`/`FAILED`/`CANCELLED` the local slot is released and the Control API releases
the node back to `IDLE`. `GET /jobs/{id}/download` serves `output/output.mp4` only when
the job is `DONE`.

Auth: `start`/`cancel` require a Bearer token — the job's upload token (validated with
the Control API) or this node's `NODE_TOKEN`. `status`/`download` are read-only and
authorized by the unguessable job UUID (capability URL).

Pipeline secrets (`GROQ_API_KEY`, `GEMINI_API_KEY`) and ffmpeg tuning come from the same
`.env`. The `video_pipeline` package is auto-added to `sys.path` in the monorepo layout;
override its location with `VIDEO_PIPELINE_PATH`.

```powershell
cd services\vps-agent
python scripts\test_phase10.py   # no ffmpeg / API keys / Control API needed
```

For a real end-to-end run, install the pipeline's deps and `ffmpeg`/`ffprobe`, set the
API keys, then: create a job (control-api) → upload → `start` → poll `status` → `download`.
