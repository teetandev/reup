# Error Model

## Standard Error

```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File exceeds the 500MB limit.",
    "details": {
      "max_file_mb": 500
    }
  }
}
```

## Common Error Codes

Auth:
```text
INVALID_SECRET_KEY
KEY_REVOKED
USER_BLOCKED
UNAUTHORIZED
FORBIDDEN
```

Job:
```text
USER_LIMIT_REACHED
DAILY_LIMIT_REACHED
NO_NODE_AVAILABLE
JOB_NOT_FOUND
JOB_NOT_OWNED
INVALID_JOB_STATUS
JOB_CANCELLED
```

`USER_LIMIT_REACHED` (concurrent) and `DAILY_LIMIT_REACHED` (per-day) are both
`409` and carry quota diagnostics in `details`:

```json
{
  "error": {
    "code": "USER_LIMIT_REACHED",
    "message": "Bạn đang có 1/1 job đang chạy. ...",
    "details": {
      "active_jobs_count": 1,
      "active_jobs_limit": 1,
      "daily_jobs_count": 1,
      "daily_jobs_limit": 10,
      "stuck_job_ids": ["<uuid>"]
    }
  }
}
```

Quota rules:

- Only **active** statuses (`ASSIGNED_NODE`, `WAITING_UPLOAD`, `UPLOADING`,
  `UPLOADED`, `EXTRACTING_AUDIO`…`RENDERING`) count toward the concurrent limit.
- The daily limit counts active + `DONE` jobs created today; `FAILED`,
  `CANCELLED`, `EXPIRED` (incl. failed uploads) never consume daily quota.
- Jobs stuck in a pre-upload state with no completed upload past
  `STALE_JOB_TIMEOUT_MINUTES` (default 30) are auto-expired (`UPLOAD_TIMEOUT`)
  on the next `POST /jobs` and stop counting. Admins can force this via
  `POST /admin/jobs/cleanup-stale`.
- `ADMIN` role users bypass quota entirely.

Node:
```text
NODE_NOT_FOUND
NODE_OFFLINE
NODE_DISABLED
NODE_BUSY
NODE_AUTH_FAILED
NODE_STALE
```

Upload:
```text
UPLOAD_TOKEN_INVALID
UPLOAD_TOKEN_EXPIRED
FILE_TOO_LARGE
UNSUPPORTED_FILE_TYPE
NO_AUDIO_STREAM
DISK_SPACE_LOW
UPLOAD_FAILED
```

Pipeline:
```text
FFPROBE_FAILED
EXTRACT_AUDIO_FAILED
CHUNK_AUDIO_FAILED
TRANSCRIBE_FAILED
TRANSLATE_FAILED
SRT_GENERATION_FAILED
RENDER_FAILED
OUTPUT_VERIFY_FAILED
```

System:
```text
CONFIG_ERROR
DATABASE_ERROR
INTERNAL_ERROR
```
