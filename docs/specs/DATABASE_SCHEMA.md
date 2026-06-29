# Database Schema — PostgreSQL/Supabase

## Enums

```sql
CREATE TYPE user_status AS ENUM ('ACTIVE', 'BLOCKED');
CREATE TYPE user_role AS ENUM ('USER', 'ADMIN');

CREATE TYPE api_key_status AS ENUM ('ACTIVE', 'REVOKED');

CREATE TYPE node_status AS ENUM (
  'PROVISIONING',
  'IDLE',
  'BUSY',
  'OFFLINE',
  'DISABLED',
  'ERROR'
);

CREATE TYPE job_status AS ENUM (
  'CREATED',
  'ASSIGNED_NODE',
  'WAITING_UPLOAD',
  'UPLOADING',
  'UPLOADED',
  'EXTRACTING_AUDIO',
  'CHUNKING_AUDIO',
  'TRANSCRIBING',
  'TRANSLATING',
  'GENERATING_SRT',
  'RENDERING',
  'DONE',
  'FAILED',
  'CANCELLED',
  'EXPIRED'
);
```

## users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name TEXT NOT NULL,
  role user_role NOT NULL DEFAULT 'USER',
  status user_status NOT NULL DEFAULT 'ACTIVE',

  max_file_mb INTEGER NOT NULL DEFAULT 500,
  max_concurrent_jobs INTEGER NOT NULL DEFAULT 1,
  daily_job_limit INTEGER NOT NULL DEFAULT 10,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## api_keys

User secret keys. Store hash only.

```sql
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  key_prefix TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  status api_key_status NOT NULL DEFAULT 'ACTIVE',

  name TEXT,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

## vps_nodes

```sql
CREATE TABLE vps_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  name TEXT NOT NULL,
  public_url TEXT NOT NULL UNIQUE,

  status node_status NOT NULL DEFAULT 'PROVISIONING',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,

  max_jobs INTEGER NOT NULL DEFAULT 1,
  current_job_id UUID,

  node_token_prefix TEXT,
  node_token_hash TEXT,

  agent_version TEXT,
  cpu_percent NUMERIC,
  ram_used_mb INTEGER,
  ram_total_mb INTEGER,
  disk_free_gb NUMERIC,

  last_heartbeat_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vps_nodes_status ON vps_nodes(status);
CREATE INDEX idx_vps_nodes_enabled ON vps_nodes(enabled);
CREATE INDEX idx_vps_nodes_last_heartbeat ON vps_nodes(last_heartbeat_at);
```

## jobs

```sql
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id UUID NOT NULL REFERENCES users(id),
  api_key_id UUID REFERENCES api_keys(id),
  node_id UUID REFERENCES vps_nodes(id),

  status job_status NOT NULL DEFAULT 'CREATED',
  current_step TEXT,
  progress_percent NUMERIC NOT NULL DEFAULT 0,

  original_filename TEXT,
  file_size_bytes BIGINT,
  duration_seconds NUMERIC,
  resolution TEXT,

  upload_token_hash TEXT,
  upload_token_expires_at TIMESTAMPTZ,

  node_upload_url TEXT,
  node_download_url TEXT,

  error_code TEXT,
  error_message TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  assigned_at TIMESTAMPTZ,
  upload_started_at TIMESTAMPTZ,
  upload_completed_at TIMESTAMPTZ,
  processing_started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_node_id ON jobs(node_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

## job_events

Append-only log of job lifecycle.

```sql
CREATE TABLE job_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  node_id UUID REFERENCES vps_nodes(id),

  event_type TEXT NOT NULL,
  message TEXT,
  data JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_job_events_job_id ON job_events(job_id);
CREATE INDEX idx_job_events_created_at ON job_events(created_at);
```

## admin_audit_logs

```sql
CREATE TABLE admin_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  admin_user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  target_type TEXT,
  target_id UUID,
  metadata JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Scheduler Locking Rule

When assigning a node, use a transaction:

```sql
SELECT *
FROM vps_nodes
WHERE enabled = TRUE
  AND status = 'IDLE'
  AND current_job_id IS NULL
ORDER BY last_heartbeat_at DESC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

Then update selected node:

```sql
UPDATE vps_nodes
SET status = 'BUSY',
    current_job_id = :job_id,
    updated_at = now()
WHERE id = :node_id;
```

This prevents two jobs from taking the same node.
