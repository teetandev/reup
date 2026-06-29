"""Admin (user/key management) request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    display_name: str = Field(min_length=1)
    daily_job_limit: int = Field(default=10, ge=0)
    max_file_mb: int = Field(default=500, ge=1)
    role: Literal["USER", "ADMIN"] = "USER"


class UserResponse(BaseModel):
    id: str
    display_name: str
    role: str
    status: str
    max_file_mb: int
    max_concurrent_jobs: int
    daily_job_limit: int


class IssueKeyRequest(BaseModel):
    name: str | None = None


class IssueKeyResponse(BaseModel):
    """Returned once at creation — the plaintext key is never retrievable again."""

    secret_key: str
    key_prefix: str


class RevokeKeyResponse(BaseModel):
    id: str
    status: str
