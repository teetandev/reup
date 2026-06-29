# Phase 08 — Direct Upload

```text
Implement direct upload from browser/client to VPS agent.

Control API:
- create short-lived upload token
- token binds job_id/user_id/node_id

Agent:
- verify token
- reject invalid/expired token
- stream upload
- enforce 500MB while streaming
- save file to safe job dir
- notify control API job status UPLOADED
```
