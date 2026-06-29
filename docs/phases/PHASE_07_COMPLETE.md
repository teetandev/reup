# Phase 07 — Scheduler (COMPLETE)

**Completed:** 2026-06-29

## Summary

Implemented job creation and node assignment with transactional locking in the Control API. Users can now create jobs via `POST /jobs`, which atomically assigns an idle VPS node, generates a short-lived upload token, and returns upload details.

## What Was Built

### Control API (`apps/control-api`)

**New files:**
- `app/jobs/__init__.py` — jobs module marker
- `app/jobs/service.py` — core scheduler logic:
  - `create_job()` — transactional job creation + node assignment
  - `assign_idle_node()` — SELECT ... FOR UPDATE SKIP LOCKED to prevent race conditions
  - `count_active_jobs()` — check user's concurrent job limit
  - `generate_upload_token()` — cryptographically secure token (secrets.token_urlsafe)
  - `get_job()` — fetch job with authorization check
  - `list_user_jobs()` — list user's own jobs
  - `release_node()` — helper for terminal states (not yet called by pipeline)
- `app/schemas/jobs.py` — Pydantic models:
  - `CreateJobRequest`, `CreateJobResponse`, `JobResponse`, `JobListResponse`, `UploadInfo`
- `scripts/test_scheduler.py` — comprehensive test script

**Updated files:**
- `app/routers/jobs.py` — implemented endpoints:
  - `POST /jobs` — create job, assign node, return upload details
  - `GET /jobs/{job_id}` — get single job (user sees own, admin sees all)
  - `GET /jobs` — list user's own jobs
- `app/auth/tokens.py` — added `api_key_id` to JWT payload
- `app/auth/dependencies.py` — extract `api_key_id` from JWT, store in `request.state`
- `app/routers/auth.py` — pass `api_key_id` to `create_access_token()`

## Key Features

### 1. Transactional Node Assignment

```sql
SELECT *
FROM vps_nodes
WHERE enabled = TRUE
  AND status = 'IDLE'
  AND current_job_id IS NULL
  AND last_heartbeat_at > now() - interval '60 seconds'
ORDER BY last_heartbeat_at DESC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

Race condition protection: two simultaneous `POST /jobs` calls cannot assign the same node.

### 2. User Limits Enforcement

- **File size limit:** `file_size_bytes <= user.max_file_mb * 1024 * 1024`
- **Concurrent jobs limit:** active jobs < `user.max_concurrent_jobs`
- Active statuses: ASSIGNED_NODE, WAITING_UPLOAD, UPLOADING, UPLOADED, EXTRACTING_AUDIO, CHUNKING_AUDIO, TRANSCRIBING, TRANSLATING, GENERATING_SRT, RENDERING

### 3. Upload Token Security

- Generated with `secrets.token_urlsafe(32)` (cryptographically secure)
- Stored as SHA-256 hash only (never plaintext)
- Short-lived: 30 minutes expiry (configurable via `UPLOAD_TOKEN_EXPIRES_MINUTES`)
- Token validation will be implemented in Phase 08

### 4. Job Lifecycle

```text
CREATED → ASSIGNED_NODE → WAITING_UPLOAD
```

On creation:
- Job status: `WAITING_UPLOAD`
- Node status: `BUSY`
- Node `current_job_id`: set to job ID
- Job event created: `JOB_CREATED`

### 5. Error Handling

- `FILE_TOO_LARGE` (400) — file exceeds user's max_file_mb
- `USER_LIMIT_REACHED` (409) — user has reached max_concurrent_jobs
- `NO_NODE_AVAILABLE` (409) — no idle, fresh nodes available
- `JOB_NOT_FOUND` (404) — job doesn't exist
- `JOB_NOT_OWNED` (403) — user trying to access another user's job

## API Examples

### Create Job

**Request:**
```bash
POST /jobs
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "original_filename": "movie.mp4",
  "file_size_bytes": 123456789
}
```

**Response (201):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "WAITING_UPLOAD",
  "upload": {
    "url": "https://node-1.example.com/jobs/550e8400-e29b-41d4-a716-446655440000/upload",
    "token": "abcd1234...xyz",
    "expires_at": "2026-06-29T12:30:00Z"
  }
}
```

### Get Job

**Request:**
```bash
GET /jobs/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <user_jwt>
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "...",
  "node_id": "...",
  "status": "WAITING_UPLOAD",
  "current_step": null,
  "progress_percent": 0,
  "original_filename": "movie.mp4",
  "file_size_bytes": 123456789,
  "duration_seconds": null,
  "resolution": null,
  "node_download_url": null,
  "error_code": null,
  "error_message": null,
  "created_at": "2026-06-29T12:00:00Z",
  "assigned_at": "2026-06-29T12:00:00Z",
  "upload_started_at": null,
  "upload_completed_at": null,
  "processing_started_at": null,
  "completed_at": null,
  "expires_at": null,
  "updated_at": "2026-06-29T12:00:00Z"
}
```

### List Jobs

**Request:**
```bash
GET /jobs
Authorization: Bearer <user_jwt>
```

**Response (200):**
```json
{
  "jobs": [
    { /* JobResponse */ },
    { /* JobResponse */ }
  ]
}
```

## Testing

Run the test script (requires a running PostgreSQL database):

```powershell
cd apps\control-api
python scripts\test_scheduler.py
```

Tests verify:
- ✓ Job creation succeeds
- ✓ Node is locked (BUSY, current_job_id set)
- ✓ Active job count is accurate
- ✓ File size limit is enforced
- ✓ No node available returns proper error
- ✓ User concurrent job limit is enforced
- ✓ Race condition protection works

## Security Notes

1. **Upload token stored as hash only** — plaintext never persisted
2. **Short-lived tokens** — 30-minute expiry reduces attack window
3. **User isolation** — users can only see their own jobs (unless admin)
4. **File size validation** — prevents excessive uploads
5. **Concurrent job limits** — prevents resource abuse
6. **Race condition protection** — `FOR UPDATE SKIP LOCKED` prevents double-assignment

## Known Limitations

1. **No token validation endpoint yet** — VPS agent can't validate upload tokens until Phase 08
2. **No agent status callback yet** — agent can't update job status until Phase 08
3. **No node release on completion** — `release_node()` helper exists but isn't called yet (Phase 10)
4. **No daily job limit check** — only concurrent limit is enforced (daily can be added later)
5. **No job timeout/expiry** — jobs don't auto-expire yet (Phase 14)
6. **No job queue** — when no nodes available, returns error instead of queuing (MVP)

## What's Next (Phase 08)

Implement direct upload in VPS Agent:
1. Add `POST /jobs/{job_id}/upload` endpoint in VPS agent
2. Add `POST /jobs/{job_id}/validate-token` in Control API (agent validates upload token)
3. Add `POST /jobs/{job_id}/agent-status` in Control API (agent reports progress)
4. VPS agent accepts multipart file upload
5. VPS agent validates token, saves to `{WORK_DIR}/jobs/{job_id}/input.mp4`
6. VPS agent extracts metadata with ffprobe
7. VPS agent updates job status to UPLOADED

## Changed Files

**Created:**
- apps/control-api/app/jobs/__init__.py
- apps/control-api/app/jobs/service.py
- apps/control-api/app/schemas/jobs.py
- apps/control-api/scripts/test_scheduler.py

**Updated:**
- apps/control-api/app/routers/jobs.py
- apps/control-api/app/auth/tokens.py
- apps/control-api/app/auth/dependencies.py
- apps/control-api/app/routers/auth.py
- AI_HANDOFF.md

## Acceptance Criteria ✅

From `docs/specs/ACCEPTANCE_CRITERIA.md` Phase 07:

- ✅ User can create job
- ✅ Idle node is assigned
- ✅ Node is locked transactionally
- ✅ Second simultaneous job cannot take same node
- ✅ No idle node returns clear error (NO_NODE_AVAILABLE)
- ✅ File size limit enforced (FILE_TOO_LARGE)
- ✅ User concurrent job limit enforced (USER_LIMIT_REACHED)
