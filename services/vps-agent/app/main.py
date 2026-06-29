"""VPS Agent application entrypoint.

Run with::

    uvicorn app.main:app --reload --port 8100
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .errors import AgentError, register_exception_handlers
from .heartbeat import heartbeat_enabled, heartbeat_loop
from .logging_config import configure_logging, get_logger
from .routers import health, jobs, upload
from .state import get_node_state, init_node_state


def _ensure_work_dir(settings: Settings, logger) -> Path:
    """Create the per-job working directory, failing loudly on misconfig.

    Raises ``CONFIG_ERROR`` rather than starting a node that cannot store jobs.
    """
    work_dir = Path(settings.work_dir)
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AgentError(
            500,
            "CONFIG_ERROR",
            "WORK_DIR could not be created.",
            {"work_dir": str(work_dir)},
        ) from exc
    logger.info("Agent work dir ready: %s", work_dir.resolve())
    return work_dir


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI):
    """Start/stop the background heartbeat loop alongside the app."""
    settings = get_settings()
    logger = get_logger(__name__)
    task: asyncio.Task | None = None

    if heartbeat_enabled(settings):
        task = asyncio.create_task(heartbeat_loop(get_node_state(), settings))
    else:
        logger.info(
            "Heartbeat loop disabled (set NODE_ID/NODE_TOKEN/CONTROL_API_URL and "
            "HEARTBEAT_INTERVAL_SECONDS>0 to enable)."
        )

    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    _ensure_work_dir(settings, logger)
    init_node_state(settings)

    app = FastAPI(
        title="Reup Vietsub VPS Agent",
        version=settings.agent_version,
        description="Per-node agent: direct upload, video pipeline, heartbeat, download.",
        lifespan=_lifespan,
    )

    # CORS for browser uploads (allow all origins since agents have public URLs)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(upload.router)
    app.include_router(jobs.router)

    # Never log NODE_TOKEN or any secret. node_id is safe to log.
    logger.info(
        "VPS Agent initialized (env=%s, node_id=%s, max_jobs=%s, max_file_mb=%s)",
        settings.app_env,
        settings.node_id or "<unset>",
        settings.max_jobs,
        settings.max_file_mb,
    )
    return app


app = create_app()
