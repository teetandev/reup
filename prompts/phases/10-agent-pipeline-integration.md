# Phase 10 — Agent Pipeline Integration

```text
Integrate video-pipeline into VPS agent.

Endpoints:
- POST /jobs/{job_id}/start
- GET /jobs/{job_id}/status
- GET /jobs/{job_id}/download
- POST /jobs/{job_id}/cancel

Requirements:
- update progress per step
- callback to control API
- capture errors
- release node through control API on done/failed
```
