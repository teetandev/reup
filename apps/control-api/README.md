# apps/control-api

FastAPI control server. Coordination only — no heavy video work.

Responsibilities:
- Secret-key auth (login), users, secret keys (hash only, shown once).
- Jobs lifecycle and scheduler (assign one idle VPS node per job, one job per node).
- VPS node registry, heartbeat, and stale -> OFFLINE detection.
- Short-lived upload tokens; returns the selected node's direct upload URL.

**Rules**
- Never receive 500MB video uploads (browser uploads directly to the VPS agent).
- Never run FFmpeg.
- Never store plaintext secret keys or VPS passwords.

## Status

**Phase 06 — Node Heartbeat (current).** Admin registers VPS nodes
(`POST /admin/nodes`) and gets a one-time node token + install command; only
`node_token_hash` + `node_token_prefix` are stored. `GET /admin/nodes` and
`GET /admin/nodes/{node_id}` list/view nodes and reconcile stale nodes to
`OFFLINE` (`last_heartbeat_at` older than `NODE_HEARTBEAT_STALE_SECONDS`, default
60s; `DISABLED` is never overridden). `POST /nodes/heartbeat` is node-authenticated
(`Authorization: Bearer <NODE_TOKEN>` + `node_id` in body) and upserts status,
`current_job_id`, CPU/RAM/disk, `agent_version`, and `last_heartbeat_at`. New code:
`app/auth/node_tokens.py`, `app/nodes/service.py`, `app/schemas/nodes.py`.

**Phase 04 — Secret-Key Auth.** Admin creates users and issues secret
keys (plaintext shown once, only `key_hash` + `key_prefix` stored). `POST /auth/login`
validates a key and returns a JWT; `GET /auth/me` returns the current user. Revoked
keys and blocked users cannot log in. Admin endpoints require the `X-Admin-Secret`
bootstrap header or an admin JWT.

**Phase 03 — Database Models.** SQLAlchemy models + Alembic migrations under
`app/db/` and `migrations/` matching `docs/specs/DATABASE_SCHEMA.md`.

**Phase 02 — Control API Base.** FastAPI skeleton: `/health`, config, error envelope,
logging, CORS. `jobs` / `nodes` routers are still `501 NOT_IMPLEMENTED`.

## Layout

```text
app/
  main.py            create_app() factory + module-level `app`
  config.py          Settings (pydantic-settings), get_settings()
  errors.py          ApiError + structured error handlers
  logging_config.py  configure_logging(), get_logger()
  routers/
    health.py        GET /health
    auth.py          /auth/*   (placeholder)
    admin.py         /admin/*  (placeholder)
    jobs.py          /jobs/*   (placeholder)
    nodes.py         /nodes/*  (placeholder)
  db/
    base.py          DeclarativeBase
    enums.py         status enums (user/role/api_key/node/job)
    session.py       engine + SessionLocal from DATABASE_URL, get_db()
    models.py        ORM models for all 6 tables
migrations/          Alembic (env.py, versions/0001_initial_schema.py)
alembic.ini          Alembic config (URL injected from env at runtime)
scripts/migrate.py   migration runner wrapper
```

## Database & migrations

Models/migrations match `docs/specs/DATABASE_SCHEMA.md`. The DB URL is read from
`DATABASE_URL` (via `app/config.py`) — never hard-coded.

Tables: `users`, `api_keys`, `vps_nodes`, `jobs`, `job_events`, `admin_audit_logs`.
Enums: `user_status`, `user_role`, `api_key_status`, `node_status`, `job_status`.

Requires PostgreSQL (uses UUID / JSONB / TIMESTAMPTZ / native enums; `gen_random_uuid()`
needs PG 13+ or the `pgcrypto` extension). Start a local DB, set `DATABASE_URL` in `.env`,
then run migrations from this directory:

```powershell
# Apply schema
python scripts/migrate.py upgrade            # alembic upgrade head
# or directly:
alembic upgrade head

# Other commands
python scripts/migrate.py current            # show current revision
python scripts/migrate.py downgrade -1       # roll back one
python scripts/migrate.py sql                # render SQL offline (no DB needed)
```

## Auth (Phase 04)

Endpoints: `POST /auth/login`, `GET /auth/me`, `POST /admin/users`,
`POST /admin/users/{user_id}/keys`, `POST /admin/keys/{key_id}/revoke`.
Admin auth = `X-Admin-Secret: $ADMIN_BOOTSTRAP_SECRET` header **or** an admin JWT.
New code: `app/auth/{keys,tokens,dependencies}.py`, `app/schemas/{auth,admin}.py`.

```bash
ADMIN=change-me   # = ADMIN_BOOTSTRAP_SECRET

# 1) create user
curl -sX POST localhost:8000/admin/users -H "X-Admin-Secret: $ADMIN" \
  -H 'Content-Type: application/json' -d '{"display_name":"Client A"}'

# 2) issue key (secret_key shown ONCE)
curl -sX POST localhost:8000/admin/users/<USER_ID>/keys -H "X-Admin-Secret: $ADMIN" \
  -H 'Content-Type: application/json' -d '{"name":"Main"}'

# 3) login -> JWT
curl -sX POST localhost:8000/auth/login \
  -H 'Content-Type: application/json' -d '{"secret_key":"sub_live_xxx"}'

# 4) current user
curl -s localhost:8000/auth/me -H "Authorization: Bearer <JWT>"

# 5) revoke -> subsequent login returns 403 KEY_REVOKED
curl -sX POST localhost:8000/admin/keys/<KEY_ID>/revoke -H "X-Admin-Secret: $ADMIN"
```

## Nodes & heartbeat (Phase 06)

Endpoints: `POST /admin/nodes`, `GET /admin/nodes`, `GET /admin/nodes/{node_id}`
(admin), and `POST /nodes/heartbeat` (node-authenticated). Requires a running DB.

```bash
ADMIN=change-me   # = ADMIN_BOOTSTRAP_SECRET

# 1) register a node -> returns node_token ONCE + install_command
curl -sX POST localhost:8000/admin/nodes -H "X-Admin-Secret: $ADMIN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"node-1","public_url":"https://node-1.example.com"}'
# response: { "id": "<NODE_ID>", "node_token": "node_live_xxx", "install_command": "...", ... }

# 2) agent heartbeat (node_id in body, token as bearer)
curl -sX POST localhost:8000/nodes/heartbeat \
  -H "Authorization: Bearer node_live_xxx" -H 'Content-Type: application/json' \
  -d '{"node_id":"<NODE_ID>","status":"IDLE","current_job_id":null,
       "cpu_percent":12.5,"ram_used_mb":900,"ram_total_mb":2048,
       "disk_free_gb":18.2,"agent_version":"0.1.0"}'
# -> {"ok": true, "node_id": "<NODE_ID>", "status": "IDLE"}

# 3) list nodes (stale ones show as OFFLINE)
curl -s localhost:8000/admin/nodes -H "X-Admin-Secret: $ADMIN"

# bad token -> 401 NODE_AUTH_FAILED
curl -isX POST localhost:8000/nodes/heartbeat -H "Authorization: Bearer wrong" \
  -H 'Content-Type: application/json' -d '{"node_id":"<NODE_ID>","status":"IDLE"}'
```

After registering a node, paste its `NODE_ID` + `NODE_TOKEN` into the VPS agent's
`.env`; the agent's background loop (or `scripts/send_heartbeat.py`) then keeps
`last_heartbeat_at` fresh.

## How to run

From this directory (`apps/control-api`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # real values come from env; never commit .env
uvicorn app.main:app --reload --port 8000
```

(Linux/macOS: `source .venv/bin/activate`, `cp .env.example .env`.)

## How to test

```bash
curl http://localhost:8000/health
# -> {"ok": true, "service": "control-api"}

curl -i http://localhost:8000/does-not-exist
# -> 404 {"error": {"code": "NOT_FOUND", ...}}

curl -i -X POST http://localhost:8000/auth/login
# -> 501 {"error": {"code": "NOT_IMPLEMENTED", ...}}
```

Interactive docs: <http://localhost:8000/docs>.

## Configuration

All settings load from environment / `.env` (see `.env.example`). No secrets are
hard-coded; defaults are safe placeholders only. `CORS_ORIGINS` is a
comma-separated list of allowed web origins.
