"""Heartbeat client — reports node status/resources to the Control API.

The agent POSTs to ``{CONTROL_API_URL}/nodes/heartbeat`` authenticated with the
node token (``Authorization: Bearer <NODE_TOKEN>``). The token is **never**
logged. Payload shape matches docs/specs/API_CONTRACT.md.

Two entry points:
- :func:`send_heartbeat_once` — one synchronous send (used by the manual script).
- :func:`heartbeat_loop`       — an async background loop (started from main.py).
"""

from __future__ import annotations

import asyncio

import httpx

from .config import Settings
from .logging_config import get_logger
from .resources import sample_resources
from .state import NodeState

logger = get_logger(__name__)

_HEARTBEAT_PATH = "/nodes/heartbeat"


def build_payload(state: NodeState, settings: Settings) -> dict[str, object]:
    """Assemble the heartbeat body from current node state + host resources."""
    snap = state.snapshot()
    res = sample_resources(settings.work_dir)
    return {
        "node_id": settings.node_id,
        "status": snap.status,
        "current_job_id": snap.current_job_id,
        "cpu_percent": res.cpu_percent,
        "ram_used_mb": res.ram_used_mb,
        "ram_total_mb": res.ram_total_mb,
        "disk_free_gb": res.disk_free_gb,
        "agent_version": settings.agent_version,
    }


def _auth_headers(settings: Settings) -> dict[str, str]:
    # Bearer node token. Never logged.
    return {"Authorization": f"Bearer {settings.node_token}"}


def _heartbeat_url(settings: Settings) -> str:
    return f"{settings.control_api_url.rstrip('/')}{_HEARTBEAT_PATH}"


def _missing_credentials(settings: Settings) -> str | None:
    """Return a human reason if heartbeat can't run, else ``None``."""
    if not settings.node_id:
        return "NODE_ID is not set"
    if not settings.node_token:
        return "NODE_TOKEN is not set"
    if not settings.control_api_url:
        return "CONTROL_API_URL is not set"
    return None


def send_heartbeat_once(state: NodeState, settings: Settings, timeout: float = 10.0) -> httpx.Response:
    """Send a single heartbeat synchronously and return the response.

    Raises ``RuntimeError`` if required credentials are missing, and propagates
    ``httpx`` transport errors so callers (the manual script) can report them.
    """
    reason = _missing_credentials(settings)
    if reason is not None:
        raise RuntimeError(f"Cannot send heartbeat: {reason}.")

    payload = build_payload(state, settings)
    with httpx.Client(timeout=timeout) as client:
        return client.post(
            _heartbeat_url(settings), json=payload, headers=_auth_headers(settings)
        )


async def _send_async(client: httpx.AsyncClient, state: NodeState, settings: Settings) -> None:
    payload = build_payload(state, settings)
    resp = await client.post(
        _heartbeat_url(settings), json=payload, headers=_auth_headers(settings)
    )
    if resp.status_code >= 400:
        # Log status + node id only — never the token or full token errors.
        logger.warning(
            "Heartbeat rejected (status=%s, node_id=%s)", resp.status_code, settings.node_id
        )
    else:
        logger.debug("Heartbeat ok (node_id=%s)", settings.node_id)


async def heartbeat_loop(state: NodeState, settings: Settings) -> None:
    """Background loop: send a heartbeat every ``heartbeat_interval_seconds``.

    Resilient by design — network/transport errors are logged and the loop keeps
    going. Cancel the task (on shutdown) to stop it.

    Also performs periodic job file cleanup (every ~1 hour).
    """
    interval = max(1, settings.heartbeat_interval_seconds)
    logger.info(
        "Heartbeat loop started (interval=%ss, control_api=%s, node_id=%s)",
        interval,
        settings.control_api_url,
        settings.node_id or "<unset>",
    )

    # Cleanup runs every ~1 hour (assuming 30s heartbeat interval = 120 iterations)
    cleanup_counter = 0
    cleanup_interval = 120

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                await _send_async(client, state, settings)
            except asyncio.CancelledError:
                logger.info("Heartbeat loop stopping.")
                raise
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                logger.warning("Heartbeat send failed: %s", exc)

            # Periodic cleanup of old job files
            cleanup_counter += 1
            if cleanup_counter >= cleanup_interval:
                try:
                    from .cleanup import cleanup_old_jobs
                    cleanup_old_jobs(settings, retention_days=7)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Job cleanup failed: %s", exc)
                cleanup_counter = 0

            await asyncio.sleep(interval)


def heartbeat_enabled(settings: Settings) -> bool:
    """Whether the background loop should run (credentials present + interval>0)."""
    return _missing_credentials(settings) is None and settings.heartbeat_interval_seconds > 0
