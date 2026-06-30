# Cleanup Policy (disk safety)

- **On DONE**: worker deletes `input.mp4, audio/, transcript/, translation/, subtitle/,
  metadata.json` and **keeps `output/output.mp4`** for download.
- **On download**: a FastAPI BackgroundTask deletes the **entire job folder** *after* the
  file response finishes streaming (`?cleanup=false` to skip).
- **TTL**: `OUTPUT_TTL_HOURS` (default 6). Sweep runs on startup + ~every 10 min in the
  heartbeat loop; removes whole job folders whose `output/output.mp4` mtime exceeds the TTL.
  The currently running job is never removed.
- **Safety**: every delete goes through `safe_delete_path()` which refuses anything not
  strictly inside `WORK_DIR`.

Logs: cleanup_intermediates_started/done, cleanup_after_download_scheduled/done,
ttl_cleanup_removed, ttl_cleanup_skipped_running_job.
