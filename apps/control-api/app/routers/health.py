"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    """Liveness probe. Matches docs/specs/API_CONTRACT.md."""
    return {"ok": True, "service": "control-api"}
