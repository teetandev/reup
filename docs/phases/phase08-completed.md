# Phase 08 — Direct Upload — Completion Summary

**Status:** ✅ Complete  
**Date:** 2026-06-29

## What was implemented

### Control API
- **`POST /jobs/{job_id}/validate-token`** — Node-authenticated endpoint that validates upload token hash and expiry, returns job_id/user_id/node_id if valid
- **`POST /jobs/{job_id}/agent-status`** — Node-authenticated callback for VPS agents to update job status, progress, metadata (duration, resolution), and error info
- New router: `app/routers/agent.py`
- New schemas: `app/schemas/agent.py` (ValidateTokenRequest/Response, AgentStatusUpdateRequest/Response)
- Updated `app/main.py` to include agent router

### VPS Agent
- **`POST /jobs/{job_id}/upload`** — Direct video upload endpoint with:
  - Upload token validation via Control API
  - Single-job slot acquisition (enforces MAX_JOBS=1)
  - Streaming upload with 500MB enforcement (rejects during stream, not after)
  - Safe file storage at `{WORK_DIR}/jobs/{job_id}/input.mp4`
  - Path traversal prevention (job_id validated as UUID, filename sanitized)
  - Metadata extraction with ffprobe (duration, resolution)
  - Status notifications to Control API (UPLOADING → UPLOADED)
- New router: `app/routers/upload.py`
- New service: `app/upload_service.py` with helpers:
  - `validate_upload_token()` — async HTTP call to Control API
  - `notify_control_status()` — async status update callback
  - `sanitize_filename()` — prevents path traversal
  - `extract_video_metadata()` — ffprobe wrapper
- Updated `app/main.py` to include upload router

### Test Script
- Created `scripts/test_phase08.py` for end-to-end testing

## Security measures

✅ Upload token never stored in plaintext (SHA-256 hash only)  
✅ Upload token never logged  
✅ Node token required for validate-token and agent-status endpoints  
✅ Only assigned node can update job status (verified by node_id match)  
✅ File size enforced during streaming (rejects before full upload)  
✅ Path traversal prevented (UUID validation + filename sanitization)  
✅ Original filename sanitized (removes directory components, unsafe chars)  
✅ Single-job guard enforced (node rejects if already processing)  
✅ Upload token expiry checked (30 minutes default)  

## Flow

```
1. User calls POST /jobs → Control API assigns node, generates upload token
2. Browser receives upload_url (node URL) + upload_token
3. Browser POSTs video to VPS Agent /jobs/{job_id}/upload with Bearer token
4. Agent validates token with Control API /jobs/{job_id}/validate-token
5. Agent acquires job slot (MAX_JOBS=1 enforced)
6. Agent notifies Control API: status=UPLOADING
7. Agent streams file to disk, enforcing 500MB limit
8. Agent extracts metadata with ffprobe
9. Agent notifies Control API: status=UPLOADED (with duration, resolution)
10. Agent returns success to browser
```

## Changed files

**Control API:**
- Created: `app/routers/agent.py`, `app/schemas/agent.py`
- Updated: `app/routers/__init__.py`, `app/main.py`

**VPS Agent:**
- Created: `app/routers/upload.py`, `app/upload_service.py`
- Updated: `app/routers/__init__.py`, `app/main.py`

**Scripts:**
- Created: `scripts/test_phase08.py`

**Documentation:**
- Updated: `AI_HANDOFF.md` (phase status, completed work, next prompt)

## How to run

### Control API
```powershell
cd apps\control-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: set DATABASE_URL, JWT_SECRET, etc.
python scripts\migrate.py upgrade
uvicorn app.main:app --reload --port 8000
```

### VPS Agent
```powershell
cd services\vps-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: set NODE_ID, NODE_TOKEN, CONTROL_API_URL, etc.
uvicorn app.main:app --reload --port 8100
```

### Test
```powershell
cd scripts
# Edit test_phase08.py: set USER_SECRET_KEY and NODE_TOKEN from DB
python test_phase08.py
```

Or manual test with curl:
```bash
# 1. User login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"secret_key":"sub_live_xxx"}'

# 2. Create job (save upload token)
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"original_filename":"test.mp4","file_size_bytes":10000000}'

# 3. Upload file to agent
curl -X POST http://localhost:8100/jobs/<job_id>/upload \
  -H "Authorization: Bearer <upload_token>" \
  -F "file=@test_video.mp4"

# 4. Check job status
curl http://localhost:8000/jobs/<job_id> \
  -H "Authorization: Bearer <user_token>"
```

## How to test

1. Start PostgreSQL with migrated schema
2. Create admin user and issue secret key
3. Register a VPS node (get NODE_TOKEN)
4. Start Control API on port 8000
5. Configure Agent with NODE_ID, NODE_TOKEN, CONTROL_API_URL
6. Start VPS Agent on port 8100
7. Run `python scripts/test_phase08.py` (edit credentials first)
8. Or use curl commands above with real MP4 file

## Security notes

- Upload tokens are SHA-256 hashed before storage (never plaintext)
- Upload tokens expire after 30 minutes (configurable via UPLOAD_TOKEN_EXPIRES_MINUTES)
- Node authentication required for validate-token and agent-status endpoints
- Only the assigned node can update a job (node_id verified)
- File size enforced during streaming (rejects before writing full file)
- Path traversal prevented (job_id must be valid UUID, filename sanitized)
- Upload token never appears in logs
- Node token never logged or exposed to clients

## Known limitations

1. **Not tested against live database** — Phase 08 verified by code review only. Requires PostgreSQL + both services running for full test.
2. **Synchronous token validation** — Each upload makes HTTP call to Control API (adds latency). Consider HMAC-signed tokens for Phase 14.
3. **Synchronous ffprobe** — Metadata extraction blocks upload response. For large files, consider background task.
4. **No automatic node release** — If agent crashes during upload, node stays BUSY. Scheduler handles stale nodes but no automatic cleanup yet (Phase 10/14).
5. **No partial upload resume** — If upload fails mid-stream, client must restart from beginning.
6. **No upload progress tracking** — Agent doesn't report progress percentage during upload (only UPLOADING → UPLOADED).

## Next phase

**Phase 09 — Video Pipeline**

Implement the video processing pipeline in `packages/video-pipeline`:
1. Extract audio (MP4 → MP3)
2. Chunk audio (split for Whisper 25MB limit)
3. Transcribe (Groq Whisper, Chinese)
4. Translate (Gemini, Chinese → Vietnamese)
5. Generate SRT
6. Render hardsub (burn SRT into video)

See `prompts/phases/09-video-pipeline.md` for full spec.
