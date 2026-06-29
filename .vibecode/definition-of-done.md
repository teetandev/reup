# Definition of Done

## Universal

- Runs locally.
- No hard-coded secrets.
- Env documented.
- Errors are structured.
- Docs updated.
- Manual test provided.

## Control API

- Auth protected where needed.
- DB writes are consistent.
- Scheduler lock prevents races.

## VPS Agent

- Enforces one job.
- Enforces 500MB.
- Authenticates upload token.
- Uses safe workdir paths.
- Reports progress.

## Web

- No secrets in frontend.
- Handles no-node, failed upload, failed job.
- Shows progress clearly.
