# CLAUDE.md — Reup Vietsub Operating Rules

You are the main coding agent for the Reup Vietsub project.

## Mission

Build a public website where users log in with an admin-issued secret key, upload a Chinese video, and receive a Vietnamese hardsub MP4.

## Product Constraints

- User login uses secret key only.
- Admin creates/revokes user secret keys.
- Web is deployed on free/low-cost hosting.
- Video processing happens only on VPS nodes.
- Each VPS node is 2vCPU / 2GB RAM target.
- Each VPS node runs exactly one job at a time.
- Max upload file size is 500MB.
- Browser uploads directly to selected VPS node.
- Control API coordinates only.
- Prioritize free services.
- MVP supports upload file only, not platform link scraping.

## Repo Components

```text
apps/web
  Next.js frontend and admin dashboard

apps/control-api
  FastAPI control server:
  auth, users, keys, jobs, nodes, scheduler, admin

services/vps-agent
  FastAPI agent on each VPS:
  direct upload, video pipeline, heartbeat, progress, download

packages/video-pipeline
  Python modules:
  extract audio, chunk audio, transcribe, translate, generate SRT, render

packages/shared
  Shared schemas/types/status names
```

## Existing Legacy Code

Legacy files from the current prototype:

```text
vps_server.py
  Has FastAPI render server with init/upload/start/status/download.
  Must be upgraded into services/vps-agent.
  Current in-memory JOBS is not production-ready.

main.py
  Has mp4_to_mp3 and Groq Whisper transcription.
  Contains hard-coded Windows FFmpeg path and hard-coded API key.
  Must be refactored. Never keep secrets in code.

translate.py
  Has Gemini batch translator with checkpoint/retry/JSON validation.
  Reuse this logic inside packages/video-pipeline.
```

## Absolute Rules

1. Never hard-code secrets.
2. Never store plaintext secret keys.
3. Never store plaintext VPS passwords.
4. Never run FFmpeg in apps/web.
5. Never upload 500MB videos through apps/control-api.
6. Never allow two jobs on one VPS node.
7. Never trust user-provided paths or filenames.
8. Never expose internal node tokens to frontend.
9. Never implement YouTube/TikTok/Bilibili scraping in MVP.
10. Never skip docs update after behavior change.

## Required Status Enums

Job statuses:

```text
CREATED
ASSIGNED_NODE
WAITING_UPLOAD
UPLOADING
UPLOADED
EXTRACTING_AUDIO
CHUNKING_AUDIO
TRANSCRIBING
TRANSLATING
GENERATING_SRT
RENDERING
DONE
FAILED
CANCELLED
EXPIRED
```

Node statuses:

```text
PROVISIONING
IDLE
BUSY
OFFLINE
DISABLED
ERROR
```

## Response Format After Coding

Always end with:

```text
Changed files:
How to run:
How to test:
Security notes:
Known limitations:
Next recommended prompt:
```
