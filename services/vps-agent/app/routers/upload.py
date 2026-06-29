"""Upload router: direct video upload from browser/client.

Phase 08: Implements POST /jobs/{job_id}/upload with token validation, streaming,
size enforcement, and safe file storage.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, UploadFile
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..errors import AgentError
from ..logging_config import get_logger
from ..state import NodeState, get_node_state
from ..upload_service import (
    extract_video_metadata,
    notify_control_status,
    sanitize_filename,
    validate_upload_token,
)

router = APIRouter(prefix="/jobs", tags=["upload"])
logger = get_logger(__name__)


@router.post("/{job_id}/upload")
async def upload_video(
    job_id: str,
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
    node_state: NodeState = Depends(get_node_state),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Accept direct video upload from browser/client.

    Flow:
    1. Validate upload token with Control API
    2. Acquire node job slot (enforce MAX_JOBS=1)
    3. Stream file to disk with size enforcement
    4. Extract metadata with ffprobe
    5. Update Control API (job status UPLOADED)
    6. Return success

    Security:
    - Token validated with Control API
    - File size enforced during streaming
    - Path traversal prevented
    - Original filename sanitized
    """
    # Extract token
    if not authorization or not authorization.startswith("Bearer "):
        raise AgentError(401, "UNAUTHORIZED", "Missing or invalid Authorization header.")

    upload_token = authorization[7:]

    # Validate token with Control API
    token_info = await validate_upload_token(settings, job_id, upload_token)

    # Acquire job slot (enforces MAX_JOBS=1)
    try:
        node_state.acquire_job(job_id)
    except AgentError:
        raise
    except Exception as exc:
        logger.exception("Failed to acquire job slot: %s", exc)
        raise AgentError(500, "INTERNAL_ERROR", "Failed to acquire job slot.") from exc

    # Notify Control API: UPLOADING
    try:
        await notify_control_status(
            settings,
            job_id,
            status="UPLOADING",
            message="Upload started",
        )
    except Exception as exc:
        logger.warning("Failed to notify upload start: %s", exc)

    # Prepare job directory
    job_dir = Path(settings.work_dir) / "jobs" / job_id
    try:
        job_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        node_state.release_job(job_id)
        raise AgentError(
            500,
            "DISK_SPACE_LOW",
            "Failed to create job directory.",
            {"job_dir": str(job_dir)},
        ) from exc

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename or "video.mp4")
    input_path = job_dir / "input.mp4"

    # Stream upload with size enforcement
    try:
        bytes_written = 0
        max_bytes = settings.max_file_bytes

        with open(input_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break

                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    # Cleanup partial file
                    f.close()
                    input_path.unlink(missing_ok=True)
                    node_state.release_job(job_id)
                    raise AgentError(
                        413,
                        "FILE_TOO_LARGE",
                        f"File exceeds the {settings.max_file_mb}MB limit.",
                        {
                            "max_file_mb": settings.max_file_mb,
                            "bytes_written": bytes_written,
                        },
                    )

                f.write(chunk)

        logger.info("Upload complete: job=%s, bytes=%d, path=%s", job_id, bytes_written, input_path)

    except AgentError:
        raise
    except Exception as exc:
        # Cleanup on failure
        input_path.unlink(missing_ok=True)
        node_state.release_job(job_id)
        logger.exception("Upload failed: %s", exc)
        raise AgentError(500, "UPLOAD_FAILED", "File upload failed.") from exc

    # Extract metadata with ffprobe
    try:
        metadata = extract_video_metadata(settings, str(input_path))
        duration = metadata.get("duration_seconds")
        resolution = metadata.get("resolution")
    except Exception as exc:
        logger.warning("Failed to extract video metadata: %s", exc)
        duration = None
        resolution = None

    # Notify Control API: UPLOADED
    try:
        await notify_control_status(
            settings,
            job_id,
            status="UPLOADED",
            message="Upload completed successfully",
            duration_seconds=duration,
            resolution=resolution,
        )
    except Exception as exc:
        logger.error("Failed to notify upload completion: %s", exc)
        # Don't fail the upload if notification fails

    return JSONResponse(
        status_code=200,
        content={
            "status": "UPLOADED",
            "job_id": job_id,
            "bytes_received": bytes_written,
            "duration_seconds": duration,
            "resolution": resolution,
        },
    )
