# Agency Agents — Reup Vietsub

These markdown files are **workflow prompts / Claude agent personas**, copied directly
from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents).

> They are **NOT** a runtime dependency. Nothing in `apps/`, `services/`, or
> `packages/` imports them. They are guidance prompts used when working on the repo
> with an AI coding assistant. Do not bundle them into any production build.

## Attribution & License
- Source: https://github.com/msitarzewski/agency-agents (MIT License)
- License copy: `docs/agents/THIRD_PARTY_LICENSES/agency-agents-LICENSE.md`
- YAML frontmatter and agent content are kept intact as copied.

## Copied agents (`.claude/agents/agency-agents/`)
| File | Use in Reup Vietsub |
|------|---------------------|
| engineering-backend-architect.md | Control API, DB schema, node lifecycle, scheduler |
| engineering-frontend-developer.md | Web/Admin UI polish, components, UX states |
| engineering-software-architect.md | Overall architecture review (Vercel/Render/Supabase/worker) |
| engineering-devops-automator.md | Codespace one-command setup, ports, CI/deploy |
| engineering-database-optimizer.md | Postgres schema/index review |
| engineering-ai-engineer.md | Groq Whisper + Gemini pipeline tuning |
| engineering-code-reviewer.md | PR review pass |
| engineering-technical-writer.md | Runbooks / docs |
| engineering-rapid-prototyper.md | Quick feature spikes |
| security-appsec-engineer.md | Token/secret handling, logging review |
| security-architect.md | Threat model for node tokens / upload flow |
| testing-api-tester.md | Control API + worker endpoint tests |
| product-manager.md | Scope & acceptance criteria |
| design-ux-architect.md / design-ui-designer.md | Dashboard UX/UI |

## How to use
Reference an agent by name when prompting the assistant, e.g.
"Use the Backend Architect agent to audit node assignment and heartbeat release."
See `AGENTS.md` at the repo root for ready-to-paste prompts.
