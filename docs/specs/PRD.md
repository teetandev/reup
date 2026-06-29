# PRD — Reup Vietsub

## 1. Product Vision

Build a web tool that automatically converts Chinese videos into Vietnamese hardsub MP4 files.

Target user:
- Someone who has a video file and wants Vietnamese subtitles burned into the video.
- User does not need to manually create subtitle files.
- User receives access through an admin-issued secret key.

## 2. MVP Scope

### Included

```text
- Secret-key login
- Admin creates user
- Admin issues/revokes secret key
- User uploads video file up to 500MB
- System transcribes Chinese audio
- System translates to Vietnamese
- System generates SRT
- System burns hardsub into MP4
- User downloads final video
- Admin manages VPS nodes
- Scheduler assigns job to idle VPS
- Each VPS runs one job
- Node heartbeat/status
- Job progress tracking
- Local file storage on VPS
- Cleanup expired jobs
```

### Excluded from MVP

```text
- YouTube/TikTok/Bilibili/Facebook link downloading
- DRM/private video bypass
- Payment
- Public registration
- Email verification
- Subtitle manual editor
- Dubbing/voice clone
- Mobile app
- Multiple output formats
```

## 3. User Roles

### User

Can:
- Login with secret key
- Upload video
- Start job
- View job progress
- Download output
- View own job history

Cannot:
- Create keys
- Manage nodes
- See other users' jobs
- Choose arbitrary node manually
- Access raw node token

### Admin

Can:
- Create users
- Issue/revoke secret keys
- Block users
- Add/disable/remove VPS nodes
- View node live/busy/offline status
- View current job per node
- View all jobs/logs
- Cancel/retry jobs
- Generate install command for node

## 4. Main User Journey

```text
1. Admin creates user and issues secret key.
2. User opens website.
3. User enters secret key.
4. Web validates key with control API.
5. User selects video file.
6. User clicks Start.
7. Control API checks quota and finds idle VPS.
8. Control API returns direct node upload URL.
9. Browser uploads file directly to VPS agent.
10. Agent validates token and file size.
11. Agent processes pipeline.
12. Web polls job status.
13. User downloads MP4 when done.
```

## 5. No Node Available Behavior

When all VPS nodes are busy:

MVP option:
```text
Return NO_NODE_AVAILABLE and tell user to try later.
```

Later option:
```text
Create QUEUED job and assign automatically when node becomes idle.
```

For MVP, prefer simple `NO_NODE_AVAILABLE`.

## 6. File Limits

```text
Max file size: 500MB
Recommended max duration MVP: 60 minutes
Recommended max resolution MVP: 1080p
Supported extensions MVP: mp4, mov, mkv, webm
```

## 7. Success Metrics

```text
- User can complete one full video job.
- Admin can see VPS status accurately.
- No two jobs run on same VPS.
- Failed job shows clear error.
- Output video downloads successfully.
- Files are cleaned up after expiry.
```
