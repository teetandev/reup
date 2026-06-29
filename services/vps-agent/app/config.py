"""VPS Agent configuration loaded from environment / .env.

Phase 05: config + validation only. No secret values are committed in code —
every field has a safe placeholder default and real values come from the
environment (see ``.env.example`` / ``templates/env``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent settings, sourced from environment variables / .env.

    Field names map to UPPER_CASE env vars case-insensitively
    (e.g. ``NODE_TOKEN`` -> ``node_token``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Runtime
    app_env: str = "development"
    agent_port: int = 8100
    log_level: str = "INFO"
    agent_version: str = "0.1.0"

    # Node identity / control-plane wiring.
    # NODE_ID + NODE_TOKEN are issued by the Control API when a node is registered
    # (Phase 06). They are required in production; empty defaults keep local dev
    # runnable. NODE_TOKEN is a secret — never log it, never expose it to clients.
    node_id: str = ""
    node_token: str = ""
    control_api_url: str = "http://localhost:8000"
    agent_public_url: str = "http://localhost:8100"

    # Heartbeat: how often (seconds) the agent reports status/resources to the
    # Control API. 0 disables the background loop (manual script still works).
    heartbeat_interval_seconds: int = 30

    # Job limits — one job per node is an absolute rule (CLAUDE.md rule 6).
    max_jobs: int = 1
    max_file_mb: int = 500

    # Working directory for per-job files (input/audio/output). Created on startup.
    work_dir: str = "agent_work"

    # FFmpeg / FFprobe binaries (used from the pipeline phase onward).
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    ffmpeg_threads: int = 1
    ffmpeg_preset: str = "ultrafast"
    ffmpeg_crf: int = 28

    @field_validator("max_jobs")
    @classmethod
    def _enforce_single_job(cls, value: int) -> int:
        """Hard rule: a node may never run more than one job at a time."""
        if value != 1:
            raise ValueError("MAX_JOBS must be exactly 1 (one job per node).")
        return value

    @field_validator("max_file_mb")
    @classmethod
    def _positive_max_file(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("MAX_FILE_MB must be a positive integer.")
        return value

    @property
    def max_file_bytes(self) -> int:
        """Upload size ceiling in bytes."""
        return self.max_file_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env once per process)."""
    return Settings()
