"""Pipeline configuration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class PipelineConfig(BaseSettings):
    """Video pipeline configuration from environment."""

    FFMPEG_BIN: str = "ffmpeg"
    FFPROBE_BIN: str = "ffprobe"
    FFMPEG_THREADS: int = 1
    FFMPEG_PRESET: str = "ultrafast"
    FFMPEG_CRF: int = 28

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "whisper-large-v3"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    TRANSLATION_BATCH_SIZE: int = 50

    MAX_CHUNK_DURATION_SEC: int = 300
    MAX_CHUNK_SIZE_MB: int = 20

    # LOCAL E2E ONLY — when true, the transcription (Groq/Whisper) and translation
    # (Gemini) steps are stubbed with deterministic placeholder text so the full
    # pipeline (extract -> chunk -> SRT -> hardsub render) can be exercised end to
    # end without real API keys. FFmpeg is still required. Default is False so
    # production behaviour is unchanged; enable only via MOCK_AI=true in a local
    # .env / environment. See docs/runbooks/E2E_LOCAL_TEST.md.
    MOCK_AI: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


_config = None


def get_config() -> PipelineConfig:
    """Get singleton config instance."""
    global _config
    if _config is None:
        _config = PipelineConfig()
    return _config
