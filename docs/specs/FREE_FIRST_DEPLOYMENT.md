# Free-First Deployment Plan

## Recommended MVP Services

```text
Frontend:
  Cloudflare Pages or Vercel free tier

Control API:
  Small free/cheap Python host if available, or one small VPS

Database:
  Supabase Free Postgres

Queue:
  Use Postgres locking first
  Add Upstash Redis Free later if needed

VPS Agent:
  Your Ubuntu 2vCPU/2GB VPS nodes

Storage:
  Local VPS disk in MVP
  Cloudflare R2/S3 later
```

## Why Local VPS Storage First

Free object storage is limited and video files are large.

Each 500MB input can create:

```text
input: 500MB
audio/chunks: 50–150MB
output: 300MB–1.5GB
logs/json/srt: small
```

Therefore storage on the processing VPS is simplest for MVP.

## HTTPS Requirement

If website is HTTPS, upload node URL should also be HTTPS.

Recommended:
```text
Cloudflare Tunnel per VPS node
```

## MVP Deployment Layout

```text
Cloudflare Pages:
  apps/web

Supabase:
  Postgres

VPS Node 1:
  services/vps-agent
  FFmpeg

VPS Node 2:
  services/vps-agent
  FFmpeg
```

## Scaling Later

```text
- Add more VPS nodes
- Add Redis queue
- Add R2/S3 output storage
- Add worker priority
- Add per-user quotas/payment
```
