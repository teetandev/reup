# Acceptance Criteria

## Phase 1 — Repo Structure

Done when:
```text
- folders exist
- docs exist
- env examples exist
- README explains architecture
```

## Phase 2 — Control API Base

Done when:
```text
- FastAPI starts
- GET /health returns ok
- config loads from env
- error model exists
```

## Phase 3 — Database Models

Done when:
```text
- models/migrations created
- enums match specs
- indexes exist
- local migration runs
```

## Phase 4 — Secret-Key Auth

Done when:
```text
- admin can create user
- admin can issue key
- plaintext key shown once only
- DB stores hash only
- user can login with key
- revoked key cannot login
```

## Phase 5 — VPS Agent Base

Done when:
```text
- agent starts
- GET /health works
- node config from env
- max jobs = 1 enforced
- structured errors returned
```

## Phase 6 — Node Heartbeat

Done when:
```text
- admin registers node
- agent sends heartbeat
- control API updates node status
- stale node becomes OFFLINE
```

## Phase 7 — Scheduler

Done when:
```text
- user creates job
- idle node assigned
- node locked
- second simultaneous job cannot take same node
- no idle node returns clear error
```

## Phase 8 — Direct Upload

Done when:
```text
- control returns upload_url and token
- browser/curl uploads directly to agent
- agent rejects invalid token
- agent rejects >500MB
- agent saves input under job folder
```

## Phase 9 — Video Pipeline

Done when:
```text
- sample video extracts audio
- audio chunks created
- transcript generated
- translation generated
- SRT generated
- output MP4 rendered
```

## Phase 10 — Agent Integration

Done when:
```text
- POST start triggers pipeline
- progress updates per step
- DONE job has downloadable output
- FAILED job records step/error
- node releases after done/failed
```

## Phase 11 — User Web UI

Done when:
```text
- user logs in with secret key
- user creates job
- upload progress visible
- job progress visible
- output download works
```

## Phase 12 — Admin Dashboard

Done when:
```text
- admin manages users/keys
- admin sees nodes
- admin sees jobs
- admin sees node current job
- admin can disable node
```

## Phase 13 — Install Node Script

Done when:
```text
- fresh Ubuntu VPS can install agent
- systemd service starts
- health endpoint works
- heartbeat appears in admin
```

## Phase 14 — Hardening

Done when:
```text
- security review completed
- cleanup implemented
- path traversal tested
- secret logs checked
- upload token expiry tested
```
