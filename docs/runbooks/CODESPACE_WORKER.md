# Codespace Worker Runbook
# docs/runbooks/CODESPACE_WORKER.md

# Codespace Worker — Setup & Operations Runbook

> **Primary worker mode for free/test environments.**  
> No VPS needed. A GitHub Codespace acts as the VPS Agent node.  
> VPS deployment (`scripts/install-node.sh`) remains available as a **legacy / production** option.

---

## Overview

A GitHub Codespace runs the `services/vps-agent` (FastAPI/uvicorn) on port 8100.  
The Codespace's **public** forwarded URL (`https://<name>-8100.app.github.dev`) is registered as a node in the Admin Dashboard.  
The Control API assigns jobs to this node, the user uploads the video directly to the Codespace worker, the pipeline runs, and the hardsub output is downloadable.

```
Browser ──────────────────────────────────────────────►  Control API (VPS/cloud)
  │  login / create job                                          │
  │                                                              │ assign node
  │  upload file ──────────────────────────────────────►  Codespace Worker :8100
  │                                                              │ pipeline (FFmpeg + AI)
  │  poll status ◄─────────────────────────── callbacks ◄───────┘
  │  download output ◄─────────────────────────────────────────── Codespace Worker :8100
```

---

## Prerequisites

| Item | Notes |
|------|-------|
| GitHub account | Free plan is fine |
| Repository forked or cloned | `https://github.com/teetandev/reup` |
| Control API running | Local (`localhost:8000`) or hosted |
| Admin Dashboard access | For registering the node |

---

## Step 1 — Create a Codespace

1. Go to `https://github.com/teetandev/reup`
2. Click **Code → Codespaces → Create codespace on main**
3. The `devcontainer.json` auto-provisions:
   - Python 3.11
   - FFmpeg + ffprobe
   - tmux
   - venv at `services/vps-agent/.venv`
   - requirements installed
   - `.env` created from `.env.example` (if missing)

> This takes ~2–3 minutes on first creation.

---

## Step 2 — Configure `.env`

Open `services/vps-agent/.env` in the Codespace editor (or use `services/vps-agent/.env.codespace` as a reference template).

**Minimum required values:**

```bash
APP_ENV=development
NODE_ID=codespace-agent-01          # pick any unique name
NODE_TOKEN=<from Admin Dashboard>   # fill AFTER Step 3
CONTROL_API_URL=https://your-control-api.example.com
AGENT_PUBLIC_URL=https://<codespace-name>-8100.app.github.dev  # fill AFTER Step 4
AGENT_PORT=8100
HEARTBEAT_INTERVAL_SECONDS=30
MAX_JOBS=1
MAX_FILE_MB=500
WORK_DIR=/workspaces/reup/.worker/jobs
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
FFMPEG_THREADS=3
FFMPEG_PRESET=ultrafast
FFMPEG_CRF=28
MOCK_AI=true           # set false + add real API keys for production
```

> **Never add `GROQ_API_KEY` or `GEMINI_API_KEY` to the frontend.**  
> They live only in this `.env` on the worker.

---

## Step 3 — Register Node in Admin Dashboard

1. Open the Admin Dashboard → **Nodes** → **Register New Node**
2. Fill in:
   - **Name:** `codespace-agent-01` (must match `NODE_ID`)
   - **Public URL:** `https://<codespace-name>-8100.app.github.dev` *(placeholder for now — update after Step 4)*
3. Copy the generated **Node Token** and paste it into `NODE_TOKEN` in `.env`

---

## Step 4 — Start the Worker

In the Codespace terminal:

```bash
# Foreground (good for debugging):
bash /workspaces/reup/scripts/start-codespace-worker.sh

# Background via tmux (good for persistence):
bash /workspaces/reup/scripts/start-codespace-worker.sh --bg

# Attach to tmux session:
tmux attach -t reup-worker
# Detach: Ctrl+B, then D
```

---

## Step 5 — Set Port 8100 to Public

1. In VS Code (Codespace), open the **Ports** panel (bottom bar or View → Ports)
2. Find port `8100`
3. Right-click → **Port Visibility** → **Public**
4. Copy the forwarded URL (format: `https://<codespace-name>-8100.app.github.dev`)
5. Paste this URL into:
   - `AGENT_PUBLIC_URL` in `services/vps-agent/.env`
   - The node's **Public URL** field in Admin Dashboard (update if already registered)

> ⚠️ The port resets to **Private** on Codespace restart. You must repeat this step after every restart.

---

## Step 6 — Verify Worker is Running

```bash
# Inside Codespace:
bash /workspaces/reup/scripts/check-codespace-worker.sh

# Or manually:
curl http://localhost:8100/health
curl http://localhost:8100/status

# From the internet (after setting port to Public):
curl https://<codespace-name>-8100.app.github.dev/health
```

Expected `/health` response:
```json
{"status": "ok"}
```

Expected `/status` response includes `node_id`, `max_jobs`, `current_jobs`, `uptime`.

---

## Step 7 — Run a Test Job

### Via the Web UI
1. Login as a user at `http://localhost:3000` (or your hosted frontend)
2. Click **Upload Video Mới**
3. Select a small MP4 file (< 10 MB recommended for testing)
4. Watch progress: `UPLOADING → EXTRACTING_AUDIO → ... → DONE`
5. Download the hardsub output

### Via CLI (using e2e scripts)
```bash
# From the repo root on your local machine or another terminal:
python scripts/e2e_bootstrap.py \
  --control-api https://your-control-api.example.com \
  --admin-secret <ADMIN_BOOTSTRAP_SECRET> \
  --node-public-url https://<codespace-name>-8100.app.github.dev

python scripts/e2e_run.py \
  --control-api https://your-control-api.example.com \
  --secret-key <SECRET_KEY>
```

---

## Codespace Restart Persistence

| What survives restart | What resets |
|-----------------------|-------------|
| Repo files, `.env`, `.worker/jobs/` | Port 8100 visibility (resets to Private) |
| venv and installed packages (usually) | tmux sessions |
| Git history | Running uvicorn process |

**After every restart:**
1. Re-run the start script
2. Re-set port 8100 to **Public**
3. Update `AGENT_PUBLIC_URL` if the Codespace name changed (rare)

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/health` returns connection refused | Worker is not running — run start script |
| `/health` works locally but not via public URL | Port 8100 is still **Private** — set to Public |
| `INPUT_NOT_FOUND` on job start | Video was not uploaded yet — upload first |
| Heartbeat not appearing in Admin | Check `CONTROL_API_URL` and `NODE_TOKEN` in `.env` |
| `NameError` or import errors on startup | `pip install -r requirements.txt` inside `.venv` |
| MOCK_AI transcription returns placeholder | Expected — set `MOCK_AI=false` + real API keys for real subs |
| `WORK_DIR` permission denied | `mkdir -p /workspaces/reup/.worker/jobs` |

---

## CORS Note

For browser-to-worker direct video uploads to work, the Control API must return the correct `AGENT_PUBLIC_URL` as the upload destination, and the VPS Agent must allow CORS from the frontend origin.

Check `services/vps-agent/app/main.py` for the `CORSMiddleware` configuration.  
If uploads fail with CORS errors, add your frontend URL to the `allow_origins` list (via an env var, not hard-coded).

---

## VPS Deployment (Legacy / Production Mode)

`scripts/install-node.sh` installs the VPS Agent on a real Ubuntu server as a systemd service.  
This is **not the primary mode** for free/test use, but is the recommended path for a production environment with a dedicated server.

See `docs/runbooks/NODE_INSTALL.md` for VPS deployment instructions.

---

## Security Checklist

- [ ] `NODE_TOKEN` is not logged anywhere
- [ ] `GROQ_API_KEY` / `GEMINI_API_KEY` are not in `.env.example` or any committed file
- [ ] Port 8100 is set to Public only when intentionally testing
- [ ] `.env` is in `.gitignore`
- [ ] `AGENT_PUBLIC_URL` uses `https://` (Codespace always provides HTTPS)
- [ ] Upload token is validated on every job start request
- [ ] Job IDs are validated as UUIDs (path traversal prevention)

---

## What Has Been Tested (Real Codespace Session)

| Test | Result |
|------|--------|
| `uvicorn app.main:app --host 0.0.0.0 --port 8100` | ✅ Started |
| `/health` | ✅ OK |
| `/status` | ✅ OK |
| `tmux` background mode | ✅ Worked |
| Manual FFmpeg render | ✅ Succeeded |
| Download output | ✅ Succeeded |
| `MAX_JOBS=1` config | ✅ Respected |
| `MOCK_AI=true` pipeline | ✅ Ran (stub text) |
| `INPUT_NOT_FOUND` on missing video | ✅ Expected error returned |

## What Still Needs Real Testing

| Test | Status |
|------|--------|
| Upload endpoint (`POST /jobs/{id}/upload`) | ⏳ Not tested |
| Heartbeat to real Control API | ⏳ Not tested |
| Frontend CORS direct upload to Codespace URL | ⏳ Not tested |
| Port visibility persistence after Codespace restart | ⏳ Not tested |
| Job status callbacks → Control API | ⏳ Not tested |
| `MOCK_AI=false` with real Groq + Gemini keys | ⏳ Not tested |
