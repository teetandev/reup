# Debug: NO_NODE_AVAILABLE

A node is assignable only when: `enabled=true`, `status=IDLE`, `current_job_id IS NULL`,
and `last_heartbeat_at` within the stale window.

## Fastest check
`GET /admin/nodes/{node_id}/debug` returns: enabled, status, current_job_id,
heartbeat_age_seconds, stale_threshold_seconds, assignable, reasons[]. The Control API also
logs a non-secret per-node diagnostic whenever assignment fails.

## Supabase query
```sql
select id,name,enabled,status,current_job_id,last_heartbeat_at,
  extract(epoch from now()-last_heartbeat_at) as hb_age
from vps_nodes order by last_heartbeat_at desc;
```
Common reasons: stale heartbeat (worker down / port not Public), busy (current_job_id set),
disabled, status != IDLE. Terminal jobs now always clear `current_job_id` (see release_node),
so a phantom busy node should self-heal on next heartbeat. Never delete a BUSY node casually.
