"""In-process per-job runtime tracking (Phase 10).

The video pipeline runs in a background thread on this node. While it runs we need
a place to record the job's current status / progress / step so that
``GET /jobs/{job_id}/status`` can answer poll requests, and so that ``cancel`` can
signal the worker cooperatively.

This is intentionally **in-memory** and **process-local**: each VPS runs exactly one
agent process and at most one job at a time (CLAUDE.md rule 6). The record outlives the
node's single-job slot so a finished job stays queryable/downloadable until the agent
restarts. State resets on restart — see AI_HANDOFF known limitations.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass
class JobRecord:
    """Mutable snapshot of one job's processing state on this node."""

    job_id: str
    status: str
    progress_percent: float = 0.0
    current_step: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    cancel_requested: bool = False

    def as_status_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "job_id": self.job_id,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
        }
        if self.error_code:
            body["error_code"] = self.error_code
        if self.error_message:
            body["error_message"] = self.error_message
        return body


class JobRegistry:
    """Thread-safe registry of :class:`JobRecord` keyed by job id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def start(self, job_id: str, status: str = "UPLOADED") -> JobRecord:
        """Register (or reset) a job as freshly started for processing."""
        with self._lock:
            rec = JobRecord(job_id=job_id, status=status, progress_percent=0.0)
            self._jobs[job_id] = rec
            return rec

    def update(self, job_id: str, **fields: object) -> JobRecord:
        """Patch non-None fields onto an existing record (created if absent)."""
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                rec = JobRecord(job_id=job_id, status=str(fields.get("status", "UPLOADED")))
                self._jobs[job_id] = rec
            for key, value in fields.items():
                if value is not None and hasattr(rec, key):
                    setattr(rec, key, value)
            return rec

    def request_cancel(self, job_id: str) -> JobRecord | None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None:
                rec.cancel_requested = True
            return rec

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            rec = self._jobs.get(job_id)
            return bool(rec and rec.cancel_requested)


_registry = JobRegistry()


def get_job_registry() -> JobRegistry:
    """Return the process-wide job registry."""
    return _registry
