# Phase 12 — Admin Dashboard — Implementation Summary

**Completed:** 2026-06-29

## Changed Files

### Frontend (apps/web/src)

**New files:**
- `components/AdminNav.tsx` — Admin navigation with role guard
- `app/admin/page.tsx` — Dashboard overview with 6 stat cards
- `app/admin/users/page.tsx` — User management UI
- `app/admin/nodes/page.tsx` — VPS node management UI
- `app/admin/nodes/[nodeId]/page.tsx` — Node detail page
- `app/admin/jobs/page.tsx` — All jobs list with filter
- `app/admin/jobs/[jobId]/page.tsx` — Job detail for admin

**Modified files:**
- `lib/api.ts` — Added admin methods: `getUser`, `revokeKey`, `toggleNodeEnabled`, `getJob`

### Backend (apps/control-api)

**Modified files:**
- `app/routers/admin.py` — Fixed `GET /admin/jobs` to return `{"jobs": [...]}` wrapper for consistency

## How to Run

### Control API (already running from Phase 11)
```powershell
cd apps\control-api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Web (already running from Phase 11)
```powershell
cd apps\web
npm run dev
# Open http://localhost:3000
```

### Admin Access
1. Create an admin user in the database or use existing admin user
2. Login with admin secret key at `/login`
3. If `user.role === 'ADMIN'`, navigate to `/admin`
4. Admin routes: `/admin`, `/admin/users`, `/admin/nodes`, `/admin/jobs`

## How to Test

### 1. Dashboard Overview
- Navigate to `/admin`
- Verify 6 stat cards display: total users, active jobs, idle/busy/offline nodes, failed jobs today
- Stats should match database state

### 2. User Management
- Go to `/admin/users`
- Click "Tạo người dùng" to create a new user
- After creation, click "Tạo key" on a user row
- **Critical:** Secret key appears once only in modal — copy it
- Verify key can be used to login at `/login`
- Key should not be retrievable again after closing modal

### 3. Node Management
- Go to `/admin/nodes`
- Click "Đăng ký node" to register a new VPS node
- Enter name (e.g., "node-1") and public URL (e.g., "https://node-1.example.com")
- **Critical:** Install command with node token appears once only in modal — copy it
- Node appears in list with status PROVISIONING
- Click node name to view detail page with resources, heartbeat, install command template

### 4. Job Management
- Go to `/admin/jobs`
- View all jobs from all users (not just own jobs)
- Use filter buttons: Tất cả / Hoàn tất / Lỗi
- Click "Chi tiết →" to view job detail page
- Job detail shows timeline, metadata, error if failed, download link if DONE

### 5. Navigation
- Verify AdminNav shows: Tổng quan, Người dùng, VPS Nodes, Jobs
- Non-admin users redirected to `/dashboard` when accessing admin routes
- Admin can logout and return to login page

## Required Env Vars

### apps/web/.env
```env
NEXT_PUBLIC_CONTROL_API_URL=http://localhost:8000
```

### apps/control-api/.env (unchanged)
```env
DATABASE_URL=postgresql://user:pass@localhost/reup_vietsub
SECRET_KEY=your-secret-key-min-32-chars
ADMIN_SECRET=your-admin-bootstrap-secret
NODE_HEARTBEAT_STALE_SECONDS=120
```

## Security Notes

1. **Secret keys shown once only**: When admin issues a user secret key, the plaintext `secret_key` is returned once in the response and displayed in a modal. After closing the modal, it cannot be retrieved — only the hash + prefix are stored in the database.

2. **Node tokens shown once only**: When admin registers a VPS node, the plaintext `node_token` is returned once embedded in the `install_command`. After closing the modal, it cannot be retrieved — only the hash + prefix are stored.

3. **Admin role guard**: Frontend checks `localStorage.getItem('user').role === 'ADMIN'` and redirects non-admins to `/dashboard`. Backend enforces via `require_admin` dependency (X-Admin-Secret header or admin JWT).

4. **No token exposure**: Node tokens are never exposed to frontend after initial registration. Node detail page shows a template install command with `[TOKEN_HIDDEN]` placeholder.

5. **JWT reuse**: Admin uses the same JWT bearer token authentication as regular users. The only difference is the `role` claim in the token payload.

## Known Limitations

1. **No user blocking/unblocking UI**: The user list shows status but no toggle button. Backend supports `PATCH /admin/users/{id}` to change status, but not implemented in UI (can be added later).

2. **No node enable/disable UI**: Node list shows `enabled` status but no toggle button. Backend supports node enabling/disabling, but not implemented in UI (can be added later).

3. **No job cancellation**: Job detail page shows job info but cannot cancel a running job. Backend may support this, but not implemented in UI (can be added later).

4. **No job events/logs**: Job detail page shows timeline but not the detailed `job_events` log entries. Backend has `job_events` table, but no endpoint to retrieve them yet (Phase 14 or later).

5. **Simple filter only**: Jobs page has basic status filter (all/done/failed) but no date range, user, or node filters (can be added later).

6. **No pagination**: All lists load full data without pagination. Acceptable for MVP with <100 users/nodes/jobs, but will need pagination for production scale.

7. **No install script yet**: The install command is generated but the actual `install-node.sh` script does not exist yet. That is Phase 13.

8. **No real-time updates**: Dashboard stats, node list, and job list do not auto-refresh. User must manually refresh the page. Job detail page polls every 3s for updates.

## Next Recommended Prompt

Implement Phase 13 — Install Node Script only. Read `prompts/phases/13-install-node-script.md`, `docs/specs/VPS_PROVISIONING.md`, and `AI_HANDOFF.md`. Scope: create the `install-node.sh` script that the admin pastes onto a fresh Ubuntu VPS to install the VPS agent as a systemd service. The script URL (`/install-node.sh`) is already embedded in the install command returned by `POST /admin/nodes`. The script must: detect Ubuntu, install FFmpeg + Python 3.10+, create `reup-agent` user, install agent code (pull from release or copy local), write `/etc/reup-agent/.env` with `NODE_ID`, `NODE_TOKEN`, `CONTROL_API_URL`, `AGENT_PUBLIC_URL`, create systemd service, start it, print health check result. Must NOT echo the node token after setup. Must be idempotent (safe to re-run). The script lives in `scripts/install-node.sh` and is served by control-api at `GET /install-node.sh` (add minimal endpoint). Do not implement SSH-based provisioner (that is future, not MVP). End with the standard block and update `AI_HANDOFF.md`.
