# Architecture

Read the detailed specs in `docs/specs`.

## High-Level Diagram

```text
Browser
  |
  v
apps/web
  |
  v
apps/control-api
  |       \
  |        \ node heartbeat/status
  v         v
Database    services/vps-agent on VPS 1
             services/vps-agent on VPS 2
             services/vps-agent on VPS 3
```

## Core Rule

The web/control side coordinates. The VPS agent processes.

## Direct Upload

Video must be uploaded directly from browser to assigned node:

```text
Browser → VPS Agent
```

Not:

```text
Browser → Control API → VPS Agent
```

## Node Selection

Control API chooses one idle live node and locks it.
