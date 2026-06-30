"""Application configuration loaded from environment / .env.

Phase 02: config only. No secret values are committed in code — every field
has a safe placeholder default and real values come from the environment.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Control API settings, sourced from environment variables / .env.

    Field names map to UPPER_CASE env vars case-insensitively
    (e.g. ``CONTROL_API_PORT`` -> ``control_api_port``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Runtime
    app_env: str = "development"
    control_api_port: int = 8000
    log_level: str = "INFO"
    # Public base URL of this control API, used to build the node install command
    # shown to admins (VPS_PROVISIONING.md). Defaults to local dev.
    control_api_public_url: str = "http://localhost:8000"

    # Database (declared now, USED from Phase 03 onward — not touched this phase)
    database_url: str = ""

    # Auth / tokens (declared now, USED from Phase 04 onward)
    jwt_secret: str = "change-me"
    jwt_expires_minutes: int = 10080
    admin_bootstrap_secret: str = "change-me"
    upload_token_expires_minutes: int = 30

    # Scheduler
    node_heartbeat_stale_seconds: int = 60
    # A job stuck in a pre-upload state (CREATED/ASSIGNED_NODE/WAITING_UPLOAD/
    # UPLOADING) with no completed upload past this many minutes is treated as
    # abandoned: auto-expired and excluded from quota. Prevents failed browser
    # uploads (404/413) from permanently blocking a user's concurrent limit.
    stale_job_timeout_minutes: int = 30

    # CORS — comma-separated origins in env, exposed as a list via property
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated ``cors_origins`` into a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env once per process)."""
    return Settings()
