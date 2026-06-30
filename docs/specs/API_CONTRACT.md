# API Contract

## General Error Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

## Control API

### GET /health

Response:

```json
{
  "ok": true,
  "service": "control-api"
}
```

---

### POST /auth/login

Request:

```json
{
  "secret_key": "sub_live_xxx"
}
```

Response:

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "display_name": "User",
    "role": "USER"
  }
}
```

Errors:

```text
INVALID_SECRET_KEY
USER_BLOCKED
KEY_REVOKED
```

---

### POST /admin/users

Admin only.

Request:

```json
{
  "display_name": "Client A",
  "daily_job_limit": 10,
  "max_file_mb": 500
}
```

---

### POST /admin/users/{user_id}/keys

Admin only.

Request:

```json
{
  "name": "Main key"
}
```

Response:

```json
{
  "secret_key": "sub_live_xxx",
  "key_prefix": "sub_live_abcd"
}
```

Important:
- `secret_key` is shown once only.

---

### GET /admin/nodes

Admin only.

Returns nodes.

---

### POST /admin/nodes

Admin only.

Request:

```json
{
  "name": "node-1",
  "public_url": "https://node-1.example.com"
}
```

Response includes install command.

---

### Admin job management

Admin only. Used by the Root Admin → Jobs page to clear stuck jobs.

```text
GET  /admin/jobs/{job_id}          # job detail (admin view)
POST /admin/jobs/{job_id}/cancel   # → CANCELLED, releases node (idempotent)
POST /admin/jobs/{job_id}/mark-failed   # body: {"reason": "..."} → FAILED
POST /admin/jobs/cleanup-stale     # expire all stuck pre-upload jobs
```

`cleanup-stale` response:

```json
{ "expired_job_ids": ["uuid", "..."], "count": 2 }
```

Cancel / mark-failed response:

```json
{ "id": "uuid", "status": "CANCELLED", "message": "Job cancelled." }
```

---

### POST /nodes/heartbeat

Node authenticated.

Request:

```json
{
  "node_id": "uuid",
  "status": "IDLE",
  "current_job_id": null,
  "cpu_percent": 12.5,
  "ram_used_mb": 900,
  "ram_total_mb": 2048,
  "disk_free_gb": 18.2,
  "agent_version": "0.1.0"
}
```

---

### POST /jobs

User authenticated.

Request:

```json
{
  "original_filename": "movie.mp4",
  "file_size_bytes": 123456789
}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "WAITING_UPLOAD",
  "upload": {
    "url": "https://node-1.example.com/jobs/{job_id}/upload",
    "token": "short_lived_token",
    "expires_at": "timestamp"
  }
}
```

Errors:

```text
NO_NODE_AVAILABLE
USER_LIMIT_REACHED
FILE_TOO_LARGE
```

---

### GET /jobs/{job_id}

User can read own job. Admin can read all.

---

### POST /jobs/{job_id}/agent-status

Node authenticated callback.

Updates job progress/status.

## VPS Agent API

### GET /health

Response:

```json
{
  "ok": true,
  "node_id": "uuid",
  "status": "IDLE",
  "current_job_id": null
}
```

---

### GET /status

Response:

```json
{
  "node_id": "uuid",
  "status": "IDLE",
  "current_job_id": null,
  "resource": {
    "cpu_percent": 10,
    "ram_used_mb": 900,
    "ram_total_mb": 2048,
    "disk_free_gb": 18
  }
}
```

---

### POST /jobs/{job_id}/upload

Auth:
```text
Authorization: Bearer <upload_token>
```

Multipart:
```text
file=<video>
```

Response:

```json
{
  "status": "UPLOADED",
  "job_id": "uuid"
}
```

---

### POST /jobs/{job_id}/start

Auth:
```text
Authorization: Bearer <upload_token or node job token>
```

Response:

```json
{
  "status": "STARTED"
}
```

---

### GET /jobs/{job_id}/status

Response:

```json
{
  "job_id": "uuid",
  "status": "RENDERING",
  "progress_percent": 80,
  "current_step": "RENDERING"
}
```

---

### GET /jobs/{job_id}/download

Returns MP4 when job is DONE.

---

### POST /jobs/{job_id}/cancel

Cancels current job if possible.
