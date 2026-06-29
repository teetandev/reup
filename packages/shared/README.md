# packages/shared

Shared schemas, types, and status names used across the Control API, VPS agent,
and pipeline so enums never drift.

Includes (when implemented):
- Job status enum: CREATED, ASSIGNED_NODE, WAITING_UPLOAD, UPLOADING, UPLOADED,
  EXTRACTING_AUDIO, CHUNKING_AUDIO, TRANSCRIBING, TRANSLATING, GENERATING_SRT,
  RENDERING, DONE, FAILED, CANCELLED, EXPIRED.
- Node status enum: PROVISIONING, IDLE, BUSY, OFFLINE, DISABLED, ERROR.
- Shared error codes and request/response schemas.

This is a Phase 01 placeholder.
