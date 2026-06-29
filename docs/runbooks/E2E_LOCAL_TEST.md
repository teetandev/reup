# E2E Local Test Runbook (Phase 15)

Goal: bring the **whole** Reup Vietsub system up locally and run one video
through it start-to-finish — login → create job → direct upload → pipeline →
download — against a real PostgreSQL.

There are two ways to run the pipeline locally:

- **Real mode** — set `GROQ_API_KEY` + `GEMINI_API_KEY` and have `ffmpeg`/`ffprobe`
  on PATH. Produces real Vietnamese hardsubs.
- **Mock mode** (`MOCK_AI=true`) — transcription and translation are stubbed with
  placeholder text; `ffmpeg` is still required. Lets you exercise the full plumbing
  (scheduler, upload, slot guard, status callbacks, render, download) **without API
  keys**. This is local-only and never weakens production (default is `false`).

> Commands are shown for **Windows PowerShell** (the primary dev box). Bash
> equivalents are nearly identical (`cp` instead of `copy`, `export` instead of `$env:`).

---

## 0. Prerequisites

- Python 3.11+
- `ffmpeg` and `ffprobe` on PATH (`ffmpeg -version`). Required even in mock mode.
- Docker Desktop (for the throwaway PostgreSQL) **or** a local PostgreSQL 13+.
- Node.js 18+ (only if you want to test the web UI; the scripts don't need it).
- `pip install httpx` available in whatever venv you run the E2E scripts from.

---

## 1. Start PostgreSQL

```powershell
docker compose -f docker-compose.dev.yml up -d
# DB URL: postgresql://postgres:postgres@localhost:5432/reup_vietsub
```

(If you use a host PostgreSQL instead, create a `reup_vietsub` database and set
`DATABASE_URL` accordingly in step 2.)

---

## 2. Control API: configure, migrate, run

```powershell
cd apps\control-api
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# .env already points DATABASE_URL at the docker Postgres above.
# For a real local test set a stronger JWT_SECRET; ADMIN_BOOTSTRAP_SECRET stays "change-me"
# unless you change it (and pass the same value to the bootstrap script).

# Apply migrations to the live DB:
python scripts\migrate.py upgrade        # or: alembic upgrade head

# Run it:
uvicorn app.main:app --reload --port 8000
```

Verify: open <http://localhost:8000/health> → `{"ok":true,"service":"control-api"}`.

---

## 3. Bootstrap admin data (user + key + node)

In a **new terminal** (any venv with `httpx`):

```powershell
cd D:\MMO\reup
python scripts\e2e_bootstrap.py --control-api http://localhost:8000 --admin-secret change-me --node-public-url http://localhost:8100
```

This creates a user, issues a secret key, and registers a node. It prints (once):

```text
NODE_ID=...           # put in the agent .env (step 4)
NODE_TOKEN=...        # put in the agent .env (step 4)
SECRET_KEY=sub_live_… # use in step 6
```

Copy these. They are local-only secrets shown once.

---

## 4. VPS Agent: configure, run

```powershell
cd services\vps-agent
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `services\vps-agent\.env`:

```ini
NODE_ID=<from step 3>
NODE_TOKEN=<from step 3>
CONTROL_API_URL=http://localhost:8000
AGENT_PUBLIC_URL=http://localhost:8100
HEARTBEAT_INTERVAL_SECONDS=15

# IMPORTANT on Windows: the default WORK_DIR (/var/lib/reup-agent/jobs) is not
# writable. Use a local path:
WORK_DIR=D:\MMO\reup\agent_work

# Mock mode (no API keys needed). For a real test instead, set MOCK_AI=false and
# fill GROQ_API_KEY / GEMINI_API_KEY.
MOCK_AI=true
```

Run it:

```powershell
uvicorn app.main:app --reload --port 8100
```

Verify: <http://localhost:8100/health> → `{"ok":true,"node_id":...,"status":"IDLE",...}`.

> The pipeline reads its config (GROQ/GEMINI/MOCK_AI/FFMPEG_*) from the agent's
> `.env` because `uvicorn` runs with `services/vps-agent` as the working dir.

---

## 5. Confirm the node is IDLE (heartbeat working)

Wait ~15s, then:

```powershell
curl -H "X-Admin-Secret: change-me" http://localhost:8000/admin/nodes
```

The node should show `"status":"IDLE"` with a recent `last_heartbeat_at`. Only an
IDLE, fresh node is schedulable.

---

## 6. Run the full user flow

```powershell
cd D:\MMO\reup
python scripts\e2e_run.py --control-api http://localhost:8000 --secret-key <SECRET_KEY from step 3>
```

With no video argument it generates a 10-second test clip with FFmpeg. The script
logs in, creates a job, uploads **directly to the agent**, starts the pipeline,
polls status through the Control API until `DONE`, and downloads the result to
`e2e_output_<job_id>.mp4`. Expected tail:

```text
[PASS] full E2E flow completed: login -> create -> upload -> render -> download
```

To use your own Chinese video: pass its path as the last argument.

### Or test via the web UI

```powershell
cd apps\web
copy .env.example .env.local      # NEXT_PUBLIC_CONTROL_API_URL=http://localhost:8000
npm install
npm run dev                       # http://localhost:3000
```

Log in with the secret key, upload, watch progress, download.

---

## 7. Security spot-checks

- **No secrets in logs:** scan both server terminals — JWT, upload token,
  `NODE_TOKEN`, `GROQ_API_KEY`, `GEMINI_API_KEY` must never appear. The logging
  filters redact known patterns to `***REDACTED***`.
- **Path traversal rejected:** `curl http://localhost:8100/jobs/..%2F..%2Fetc%2Fpasswd/status`
  → `404 JOB_NOT_FOUND` (job_id must be a UUID).
- **File-size guard:** creating a job with `file_size_bytes` over the user limit
  → `400 FILE_TOO_LARGE`; the agent also enforces during streaming (`413`).
- **One job per node:** while a job runs, creating another job returns
  `409 NO_NODE_AVAILABLE` (the only node is BUSY).
- **Auth required:** `GET /jobs/<id>` without a Bearer JWT → `401`.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Agent won't start, `CONFIG_ERROR WORK_DIR` | `WORK_DIR` not writable. Set a local path (Windows: `D:\MMO\reup\agent_work`). |
| `NO_NODE_AVAILABLE` on create job | Node not IDLE/fresh. Check step 5; confirm agent heartbeats and `NODE_ID`/`NODE_TOKEN` match registration. |
| Job FAILS `CONFIG_ERROR` | `video_pipeline` deps missing — `pip install -r requirements.txt` in the agent venv (includes `openai`, `google-genai`). |
| Job FAILS `EXTRACT_AUDIO_FAILED` / `RENDER_FAILED` | `ffmpeg`/`ffprobe` not on PATH, or set `FFMPEG_BIN`/`FFPROBE_BIN` to full paths. |
| Job FAILS `TRANSCRIBE_FAILED`/`TRANSLATE_FAILED` in real mode | Missing/invalid `GROQ_API_KEY`/`GEMINI_API_KEY`, or set `MOCK_AI=true`. |
| Web upload blocked by CORS | Agent allows `*`; ensure you reach the agent at its `AGENT_PUBLIC_URL`. |
| `psycopg2` build error on install | Use the bundled `psycopg2-binary` (already in requirements). |

---

## Teardown

```powershell
# Ctrl-C both uvicorn processes, then:
docker compose -f docker-compose.dev.yml down       # keep data
docker compose -f docker-compose.dev.yml down -v    # wipe data
```
