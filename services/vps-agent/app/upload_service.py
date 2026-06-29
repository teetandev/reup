"""Upload service: token validation, metadata extraction, Control API notifications.

Phase 08: Helper functions for the upload flow.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

import httpx

from .config import Settings
from .errors import AgentError
from .logging_config import get_logger

logger = get_logger(__name__)


async def validate_upload_token(
    settings: Settings,
    job_id: str,
    upload_token: str,
) -> dict[str, Any]:
    """Validate upload token with Control API.

    Returns token info (job_id, user_id, node_id) on success.
    Raises AgentError on validation failure.
    """
    url = f"{settings.control_api_url.rstrip('/')}/jobs/{job_id}/validate-token"

    headers = {
        "Authorization": f"Bearer {settings.node_token}",
        "Content-Type": "application/json",
    }

    payload = {"upload_token": upload_token}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            # Never log the upload token itself
            logger.info("Upload token validated: job=%s", job_id)
            return data

        # Handle error response
        try:
            error_data = response.json()
            error_code = error_data.get("error", {}).get("code", "UPLOAD_TOKEN_INVALID")
            error_message = error_data.get("error", {}).get("message", "Token validation failed.")
        except Exception:
            error_code = "UPLOAD_TOKEN_INVALID"
            error_message = "Token validation failed."

        raise AgentError(
            response.status_code,
            error_code,
            error_message,
        )

    except AgentError:
        raise
    except Exception as exc:
        logger.exception("Failed to validate upload token: %s", exc)
        raise AgentError(
            500,
            "INTERNAL_ERROR",
            "Failed to communicate with Control API.",
        ) from exc


async def notify_control_status(
    settings: Settings,
    job_id: str,
    status: str,
    message: str | None = None,
    current_step: str | None = None,
    progress_percent: float | None = None,
    duration_seconds: float | None = None,
    resolution: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Notify Control API of job status update.

    Raises AgentError on failure.
    """
    url = f"{settings.control_api_url.rstrip('/')}/jobs/{job_id}/agent-status"

    headers = {
        "Authorization": f"Bearer {settings.node_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "status": status,
        "message": message,
        "current_step": current_step,
        "progress_percent": progress_percent,
        "duration_seconds": duration_seconds,
        "resolution": resolution,
        "error_code": error_code,
        "error_message": error_message,
        "metadata": metadata,
    }

    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code in (200, 201):
            logger.info("Status update sent: job=%s, status=%s", job_id, status)
            return

        # Handle error
        logger.error(
            "Failed to update job status: job=%s, status_code=%d",
            job_id,
            response.status_code,
        )
        raise AgentError(
            response.status_code,
            "STATUS_UPDATE_FAILED",
            "Failed to update job status with Control API.",
        )

    except AgentError:
        raise
    except Exception as exc:
        logger.exception("Failed to notify Control API: %s", exc)
        raise AgentError(
            500,
            "INTERNAL_ERROR",
            "Failed to communicate with Control API.",
        ) from exc


def sanitize_filename(filename: str) -> str:
    """Sanitize a user-provided filename to prevent path traversal.

    Strips directory components and replaces unsafe characters.
    """
    # Remove any directory path
    filename = filename.split("/")[-1].split("\\")[-1]

    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    # Ensure it's not empty
    if not filename or filename.startswith("."):
        filename = "video.mp4"

    return filename


def extract_video_metadata(settings: Settings, video_path: str) -> dict[str, Any]:
    """Extract duration and resolution from video using ffprobe.

    Returns dict with duration_seconds and resolution (e.g. "1920x1080").
    Raises AgentError on ffprobe failure.
    """
    try:
        result = subprocess.run(
            [
                settings.ffprobe_bin,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

        data = json.loads(result.stdout)

        # Extract duration
        duration = None
        if "format" in data and "duration" in data["format"]:
            try:
                duration = float(data["format"]["duration"])
            except (ValueError, TypeError):
                pass

        if duration is None and "streams" in data and len(data["streams"]) > 0:
            stream = data["streams"][0]
            if "duration" in stream:
                try:
                    duration = float(stream["duration"])
                except (ValueError, TypeError):
                    pass

        # Extract resolution
        resolution = None
        if "streams" in data and len(data["streams"]) > 0:
            stream = data["streams"][0]
            width = stream.get("width")
            height = stream.get("height")
            if width and height:
                resolution = f"{width}x{height}"

        return {
            "duration_seconds": duration,
            "resolution": resolution,
        }

    except subprocess.TimeoutExpired as exc:
        logger.error("ffprobe timeout: %s", video_path)
        raise AgentError(
            500,
            "FFPROBE_FAILED",
            "Video metadata extraction timed out.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        logger.error("ffprobe failed: %s, stderr=%s", video_path, exc.stderr)
        raise AgentError(
            500,
            "FFPROBE_FAILED",
            "Video metadata extraction failed.",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to extract video metadata: %s", exc)
        raise AgentError(
            500,
            "FFPROBE_FAILED",
            "Video metadata extraction failed.",
        ) from exc
