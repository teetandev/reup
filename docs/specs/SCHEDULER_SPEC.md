# Scheduler Specification

## Goal

Assign a user job to exactly one idle VPS node.

## Constraints

```text
- Each VPS node max_jobs = 1
- Node must be enabled
- Node must be IDLE
- Node heartbeat must be fresh
- Node current_job_id must be null
- User must not exceed max_concurrent_jobs
```

## Fresh Node Definition

A node is fresh if:

```text
now - last_heartbeat_at <= NODE_HEARTBEAT_STALE_SECONDS
```

Default:

```text
NODE_HEARTBEAT_STALE_SECONDS=60
```

If stale:
```text
status = OFFLINE
```

## Assignment Flow

```text
1. User calls POST /jobs.
2. Control API checks user status and quota.
3. Control API checks user active jobs.
4. Control API starts DB transaction.
5. Select one idle node FOR UPDATE SKIP LOCKED.
6. Create job.
7. Set node BUSY and current_job_id = job.id.
8. Generate upload token.
9. Return job_id, node public URL, upload token.
```

## Race Condition Protection

Use DB transaction and row lock:

```sql
SELECT id
FROM vps_nodes
WHERE enabled = TRUE
  AND status = 'IDLE'
  AND current_job_id IS NULL
  AND last_heartbeat_at > now() - interval '60 seconds'
ORDER BY last_heartbeat_at DESC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

## Node Release

Release node when job becomes:

```text
DONE
FAILED
CANCELLED
EXPIRED
```

Release means:

```text
node.status = IDLE
node.current_job_id = NULL
```

Unless node is disabled or offline.

## No Node Available

MVP:
```text
Return HTTP 409 NO_NODE_AVAILABLE.
```

Later:
```text
Create queued job.
```

## User Active Job Limit

For each user:

```sql
SELECT count(*)
FROM jobs
WHERE user_id = :user_id
  AND status IN (
    'ASSIGNED_NODE',
    'WAITING_UPLOAD',
    'UPLOADING',
    'UPLOADED',
    'EXTRACTING_AUDIO',
    'CHUNKING_AUDIO',
    'TRANSCRIBING',
    'TRANSLATING',
    'GENERATING_SRT',
    'RENDERING'
  );
```

If count >= `users.max_concurrent_jobs`, reject.

## Scheduler Errors

```text
USER_BLOCKED
USER_LIMIT_REACHED
NO_NODE_AVAILABLE
NODE_LOCK_FAILED
UPLOAD_TOKEN_FAILED
```
