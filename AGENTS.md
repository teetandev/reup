# Reup Vietsub — Agent Team

A senior virtual team for working on this fullstack repo (Web/Admin on Vercel,
Control API on Render, Supabase Postgres, worker on Codespace/VPS).

Agent personas live in `.claude/agents/agency-agents/` (copied from
[agency-agents](https://github.com/msitarzewski/agency-agents), MIT). They are
prompts only — **never imported into runtime code**. See `docs/agents/README.md`.

## Roles
- **Backend Architect** — Control API, DB schema, node lifecycle, scheduler, heartbeat release.
- **Frontend Developer** — Web/Admin UI, components, polling, UX states.
- **Software Architect** — end-to-end architecture (Vercel/Render/Supabase/worker).
- **DevOps Automator** — Codespace one-command setup, port 8100 HTTP/Public, deploys.
- **Security Engineer** — NODE_TOKEN / GROQ / GEMINI secret handling, logging, hashing.
- **QA / API Tester** — upload → transcribe → translate → render → cleanup flow.
- **Technical Writer** — runbooks in `docs/runbooks/`.

## Ready-to-paste prompts
- "Use **Backend Architect** to audit node assignment and heartbeat release."
- "Use **Frontend Developer** to polish the Admin VPS Nodes page."
- "Use **DevOps Agent** to improve the one-command Codespace worker setup."
- "Use **Security Agent** to review NODE_TOKEN/GROQ/GEMINI secret exposure."
- "Use **QA Agent** to test upload, Groq transcription, Gemini translation, render, cleanup."

## Runbooks
- `docs/runbooks/CODESPACE_WORKER.md` — one-command worker setup.
- `docs/runbooks/NODE_OPERATIONS.md` — node admin operations.
