"""Control API application entrypoint.

Run with::

    uvicorn app.main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .config import get_settings
from .errors import register_exception_handlers
from .logging_config import configure_logging, get_logger
from .routers import admin, agent, auth, health, jobs, nodes


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    app = FastAPI(
        title="Reup Vietsub Control API",
        version="0.1.0",
        description="Coordination API: auth, users, keys, jobs, nodes, scheduler.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(jobs.router)
    app.include_router(nodes.router)
    app.include_router(agent.router)

    @app.get("/install-node.sh", response_class=PlainTextResponse)
    async def serve_install_script():
        """Serve the VPS agent install script."""
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "install-node.sh"
        if not script_path.exists():
            return PlainTextResponse("# Install script not found\nexit 1\n", status_code=404)
        return PlainTextResponse(script_path.read_text(), media_type="text/x-shellscript")

    logger.info(
        "Control API initialized (env=%s, cors=%s)",
        settings.app_env,
        settings.cors_origin_list,
    )
    return app


app = create_app()
