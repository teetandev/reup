# apps/web

Next.js frontend + admin dashboard for Reup Vietsub.

- Users log in with an admin-issued secret key, create jobs, upload directly to a VPS node, watch progress, and download the final MP4.
- Admin manages users, secret keys, VPS nodes, and jobs (Phase 12).

**Rules**
- Never run FFmpeg here.
- Never upload 500MB videos through this app or the Control API — the browser uploads directly to the selected VPS agent.
- Talks only to the Control API (`NEXT_PUBLIC_CONTROL_API_URL`) and to per-job VPS agent upload URLs.

## Phase 11 Status

✅ User-facing pages implemented:
- Login with secret key
- Dashboard with recent jobs
- Upload new video page
- Job detail/progress page with polling
- Job history page

## Setup

```powershell
cd apps\web
npm install
copy .env.example .env
# Edit .env: set NEXT_PUBLIC_CONTROL_API_URL
npm run dev
```

Open http://localhost:3000

## Required Environment Variables

```
NEXT_PUBLIC_CONTROL_API_URL=http://localhost:8000
```

## Features

### User Pages

- `/login` - Login with secret key
- `/dashboard` - Recent jobs + upload button
- `/jobs/new` - Upload video form with progress
- `/jobs/[jobId]` - Job detail with auto-refresh every 3s
- `/jobs` - Job history table

### Upload Flow

1. User selects video (≤500MB, mp4/mov/mkv/webm)
2. Frontend calls `POST /jobs` → receives `upload_url` + `upload_token`
3. Browser uploads directly to VPS agent using XMLHttpRequest with progress tracking
4. Frontend calls `POST /jobs/{id}/start` on the agent
5. Redirect to job detail page with 3-second polling

### Status Labels (Vietnamese)

All job statuses are displayed with Vietnamese labels mapped in `src/lib/status.ts`.

## Admin Dashboard

Admin pages will be implemented in Phase 12.
