"""Pydantic schemas for job endpoints."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from ..db.enums import JobStatus


class CreateJobRequest(BaseModel):
    """POST /jobs request body."""

    original_filename: str = Field(..., min_length=1, max_length=255)
    file_size_bytes: int = Field(..., gt=0)


class UploadInfo(BaseModel):
    """Upload details returned when job is created."""

    url: str
    token: str
    expires_at: dt.datetime


class CreateJobResponse(BaseModel):
    """POST /jobs response."""

    job_id: uuid.UUID
    status: JobStatus
    upload: UploadInfo


class JobResponse(BaseModel):
    """GET /jobs/{job_id} response."""

    id: uuid.UUID
    user_id: uuid.UUID
    node_id: uuid.UUID | None
    status: JobStatus
    current_step: str | None
    progress_percent: float
    original_filename: str | None
    file_size_bytes: int | None
    duration_seconds: float | None
    resolution: str | None
    node_download_url: str | None
    error_code: str | None
    error_message: str | None
    created_at: dt.datetime
    assigned_at: dt.datetime | None
    upload_started_at: dt.datetime | None
    upload_completed_at: dt.datetime | None
    processing_started_at: dt.datetime | None
    completed_at: dt.datetime | None
    expires_at: dt.datetime | None
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """GET /jobs response."""

    jobs: list[JobResponse]
