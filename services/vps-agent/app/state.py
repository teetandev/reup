"""In-process node state and the single-job guard.

This module owns the agent's runtime status and enforces the absolute rule that
a node runs **at most one job at a time** (``MAX_JOBS=1``, CLAUDE.md rule 6).

Phase 05 only wires up the guard and exposes it via ``/health`` and ``/status``;
the upload/start endpoints that *acquire* a job slot arrive in later phases. The
guard is intentionally process-local: each VPS node runs exactly one agent
process, so an in-memory lock is the correct ownership boundary for one node.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .config import Settings
from .errors import AgentError


# Node statuses — canonical enum from CLAUDE.md / AI_HANDOFF.md §8.
PROVISIONING = "PROVISIONING"
IDLE = "IDLE"
BUSY = "BUSY"
OFFLINE = "OFFLINE"
DISABLED = "DISABLED"
ERROR = "ERROR"


@dataclass
class NodeSnapshot:
    """Immutable view of the node's current state for responses."""

    node_id: str
    status: str
    current_job_id: str | None


class NodeState:
    """Thread-safe holder for node status and the active job.

    The single-job guard lives here: :meth:`acquire_job` is the only way to take
    the node's one job slot, and it raises ``NODE_BUSY`` if a job is already
    running. All mutations are serialized by an internal lock so concurrent
    requests can never both win the slot.
    """

    def __init__(self, node_id: str, max_jobs: int = 1) -> None:
        if max_jobs != 1:
            # Defense in depth: config already enforces this, but never let a
            # mis-constructed state allow more than one concurrent job.
            raise ValueError("NodeState supports MAX_JOBS=1 only.")
        self._node_id = node_id
        self._max_jobs = max_jobs
        self._lock = threading.Lock()
        self._current_job_id: str | None = None
        self._status: str = IDLE

    @property
    def node_id(self) -> str:
        return self._node_id

    def snapshot(self) -> NodeSnapshot:
        """Return a consistent point-in-time view of the node state."""
        with self._lock:
            return NodeSnapshot(
                node_id=self._node_id,
                status=self._status,
                current_job_id=self._current_job_id,
            )

    def acquire_job(self, job_id: str) -> None:
        """Take the single job slot for ``job_id`` or raise ``NODE_BUSY``.

        Used by the upload/start flow in later phases. Atomic: only one caller
        can transition the node from IDLE to BUSY.
        """
        with self._lock:
            if self._current_job_id is not None:
                raise AgentError(
                    409,
                    "NODE_BUSY",
                    "This node is already processing a job.",
                    {"current_job_id": self._current_job_id, "max_jobs": self._max_jobs},
                )
            self._current_job_id = job_id
            self._status = BUSY

    def release_job(self, job_id: str | None = None) -> None:
        """Release the job slot and return the node to IDLE.

        If ``job_id`` is given it must match the active job, guarding against a
        stale caller releasing someone else's job.
        """
        with self._lock:
            if job_id is not None and self._current_job_id != job_id:
                raise AgentError(
                    409,
                    "INVALID_JOB_STATUS",
                    "Cannot release a job that is not the active job.",
                    {"current_job_id": self._current_job_id, "requested_job_id": job_id},
                )
            self._current_job_id = None
            self._status = IDLE

    def set_status(self, status: str) -> None:
        """Override the node status (e.g. DISABLED/ERROR) without touching the job."""
        with self._lock:
            self._status = status


_node_state: NodeState | None = None


def init_node_state(settings: Settings) -> NodeState:
    """Build (or rebuild) the process-wide node state from settings."""
    global _node_state
    _node_state = NodeState(node_id=settings.node_id, max_jobs=settings.max_jobs)
    return _node_state


def get_node_state() -> NodeState:
    """FastAPI dependency: return the initialized node state."""
    if _node_state is None:
        raise AgentError(503, "SERVICE_UNAVAILABLE", "Node state is not initialized.")
    return _node_state
