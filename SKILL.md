# SKILL.md — Spec-First Vibecode Skill

## Name

Spec-First Phased Vibecoding for Reup Vietsub

## Purpose

Prevent Claude from building the wrong architecture and force safe, incremental implementation.

## Mandatory Pre-Code Checklist

Before editing files, state:

```text
Goal:
Component:
Files to change:
Database impact:
API impact:
Security impact:
Manual test:
```

## Phase Discipline

Implement one phase only. Do not mix phases unless explicitly requested.

Order:

```text
00-review-specs
01-repo-structure
02-control-api-base
03-database-models
04-secret-key-auth
05-vps-agent-base
06-node-heartbeat
07-scheduler
08-direct-upload
09-video-pipeline
10-agent-pipeline-integration
11-user-web-ui
12-admin-dashboard
13-install-node-script
14-hardening
```

## Security Discipline

Always check:

```text
- Is this secret stored?
- Is this token logged?
- Is this file path controlled?
- Can this endpoint be called by the wrong actor?
- Can two jobs race onto one node?
- Can this upload exceed 500MB?
```

## Resource Discipline

VPS agent must be built for 2vCPU/2GB:

```text
MAX_JOBS=1
FFMPEG_THREADS=1
FFMPEG_PRESET=ultrafast
FFMPEG_CRF=28
minimum disk free check
cleanup old files
```

## Video Pipeline Discipline

Each step must save artifacts:

```text
input.mp4
audio/full_audio.mp3
audio/chunks/*.mp3
transcript.json
translated.json
subtitle.srt
output.mp4
logs/*.log
```

## End-of-Task Output

```text
Changed files:
How to run:
How to test:
Security notes:
Known limitations:
Next recommended prompt:
```
