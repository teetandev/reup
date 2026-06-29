# Reup Vietsub Vibecode Kit v2

Bộ rule/skill/prompt/spec dùng cho Antigravity IDE + Claude để triển khai website **Reup Vietsub**.

## Mục tiêu sản phẩm

Website public cho phép user đăng nhập bằng secret key do admin cấp, upload video tiếng Trung tối đa 500MB, hệ thống tự động:

```text
upload video → extract audio → transcribe tiếng Trung → dịch tiếng Việt → tạo SRT → burn hardsub → tải MP4
```

## Kiến trúc cốt lõi

```text
apps/web
  Next.js frontend + admin dashboard

apps/control-api
  FastAPI control server
  Auth, users, secret keys, jobs, VPS nodes, scheduler

services/vps-agent
  FastAPI agent chạy trên từng VPS Ubuntu
  Nhận upload trực tiếp, xử lý pipeline video, báo heartbeat/progress

packages/video-pipeline
  Module Python tái sử dụng cho extract/transcribe/translate/srt/render
```

## Cách dùng với Antigravity IDE

1. Giải nén kit này vào root repo.
2. Mở Antigravity IDE.
3. Cho Claude đọc:

```text
Read CLAUDE.md, SKILL.md, AGENTS.md, docs/specs/PRD.md, docs/specs/DATABASE_SCHEMA.md, and prompts/MASTER_PROMPT.md. Do not code yet. Review the architecture and propose Phase 1 only.
```

4. Chạy từng phase trong `prompts/phases`.
5. Sau mỗi phase, chạy review bằng `.claude/commands/03-review.md`.

## Điểm mới ở V2

So với V1, bản này bổ sung:

```text
REVIEW_V1.md
docs/specs/PRD.md
docs/specs/DATABASE_SCHEMA.md
docs/specs/UI_FLOW.md
docs/specs/PIPELINE_SPEC.md
docs/specs/SCHEDULER_SPEC.md
docs/specs/VPS_PROVISIONING.md
docs/specs/API_CONTRACT.md
docs/specs/ACCEPTANCE_CRITERIA.md
docs/specs/SECURITY_MODEL.md
docs/specs/ERROR_MODEL.md
docs/specs/JOB_LIFECYCLE.md
docs/specs/FREE_FIRST_DEPLOYMENT.md
prompts/MASTER_PROMPT.md
prompts/phases/*.md
templates/env/*.example
templates/systemd/reup-agent.service
templates/nginx/agent-node.conf
```
