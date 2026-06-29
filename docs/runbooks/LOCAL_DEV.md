# Local Dev Runbook

> For a complete, step-by-step **end-to-end** local test (real PostgreSQL via
> `docker-compose.dev.yml`, admin bootstrap, agent, and a full job run with an
> optional no-API-key **mock mode**), see
> [E2E_LOCAL_TEST.md](./E2E_LOCAL_TEST.md). The snippets below are the quick
> per-component commands.

## Local PostgreSQL

```bash
docker compose -f docker-compose.dev.yml up -d   # postgres only, port 5432
```

## Control API

```bash
cd apps/control-api
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## VPS Agent

```bash
cd services/vps-agent
cp .env.example .env
uvicorn app.main:app --reload --port 8100
```

## Web

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

## Manual Test Skeleton

```text
1. Create admin/user/key.
2. Login with secret key.
3. Register local agent as node.
4. Agent heartbeat marks node IDLE.
5. Create job.
6. Upload sample video to agent.
7. Start pipeline.
8. Poll progress.
9. Download output.
```
