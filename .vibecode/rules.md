# Vibecode Rules

## Golden Architecture

```text
apps/web → apps/control-api → scheduler → services/vps-agent → packages/video-pipeline
```

## Never Break These Rules

```text
- Never process video in web.
- Never upload video through control API.
- Never assign two jobs to one node.
- Never store plaintext secret keys.
- Never store plaintext VPS passwords.
- Never hard-code provider API keys.
```

## Before Any Code

Answer:

```text
Component:
Scope:
Files:
DB changes:
API changes:
Security risks:
Manual test:
```

## Every Endpoint

Must have:
```text
- request schema
- response schema
- error behavior
- auth requirement
```

## Every Job Step

Must update:
```text
- jobs.status
- jobs.current_step
- jobs.progress_percent
- job_events
```
