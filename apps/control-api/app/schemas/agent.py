"""Pydantic schemas for agent callback endpoints."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field

from ..db.enums import JobStatus


class ValidateTokenRequest(BaseModel):
    """Request to validate an upload token."""

    upload_token: str = Field(..., min_length=1)


class ValidateTokenResponse(BaseModel):
    """Response after validating upload token."""

    valid: bool
    job_id: uuid.UUID
    user_id: uuid.UUID
    node_id: uuid.UUID


class AgentStatusUpdateRequest(BaseModel):
    """Request from agent to update job status/progress."""

    status: JobStatus | None = None
    current_step: str | None = None
    progress_percent: float | None = Field(None, ge=0, le=100)
    duration_seconds: float | None = Field(None, gt=0)
    resolution: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    message: str | None = None
    metadata: dict | None = None


class AgentStatusUpdateResponse(BaseModel):
    """Response after updating job status."""

    job_id: uuid.UUID
    status: JobStatus
    updated_at: dt.datetime
