# Job Lifecycle

## Status Diagram

```text
CREATED
  ↓
ASSIGNED_NODE
  ↓
WAITING_UPLOAD
  ↓
UPLOADING
  ↓
UPLOADED
  ↓
EXTRACTING_AUDIO
  ↓
CHUNKING_AUDIO
  ↓
TRANSCRIBING
  ↓
TRANSLATING
  ↓
GENERATING_SRT
  ↓
RENDERING
  ↓
DONE
```

Failure can happen from any active state:

```text
ACTIVE_STATE → FAILED
ACTIVE_STATE → CANCELLED
DONE/FAILED/CANCELLED → EXPIRED
```

## Active States

```text
ASSIGNED_NODE
WAITING_UPLOAD
UPLOADING
UPLOADED
EXTRACTING_AUDIO
CHUNKING_AUDIO
TRANSCRIBING
TRANSLATING
GENERATING_SRT
RENDERING
```

## Node Release States

When job enters:

```text
DONE
FAILED
CANCELLED
EXPIRED
```

Control API should release node if the node is not disabled/offline.

## Timeout Rules

Recommended:

```text
WAITING_UPLOAD timeout: 30 minutes
UPLOADING timeout: configurable
PROCESSING timeout: based on video duration, MVP max 3 hours
DONE file expiry: 24 hours
FAILED file expiry: 6 hours
```

## Job Events

Every transition should create a job event:

```json
{
  "event_type": "STATUS_CHANGED",
  "message": "Job moved from UPLOADED to EXTRACTING_AUDIO",
  "data": {
    "from": "UPLOADED",
    "to": "EXTRACTING_AUDIO"
  }
}
```
