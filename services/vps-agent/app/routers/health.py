"""Health and status endpoints for the VPS Agent.

Both endpoints are unauthenticated liveness/observability probes. They expose
only the node id and coarse status — never the node token or any secret.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..resources import sample_resources
from ..state import NodeState, get_node_state

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(state: NodeState = Depends(get_node_state)) -> dict[str, object]:
    """Liveness probe. Matches docs/specs/API_CONTRACT.md (VPS Agent /health)."""
    snap = state.snapshot()
    return {
        "ok": True,
        "node_id": snap.node_id,
        "status": snap.status,
        "current_job_id": snap.current_job_id,
    }


@router.get("/status")
async def status(
    state: NodeState = Depends(get_node_state),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Node status + host resource info. Matches docs/specs/API_CONTRACT.md."""
    snap = state.snapshot()
    resource = sample_resources(settings.work_dir)
    return {
        "node_id": snap.node_id,
        "status": snap.status,
        "current_job_id": snap.current_job_id,
        "resource": resource.as_dict(),
    }
