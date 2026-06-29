"""Jobs router: user job creation, query, and scheduling.

Phase 07: Implements POST /jobs (scheduler + upload token), GET /jobs/{job_id},
and GET /jobs (list user's own jobs).
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..config import Settings, get_settings
from ..db.models import User
from ..db.session import get_db
from ..jobs import service
from ..schemas.jobs import (
    CreateJobRequest,
    CreateJobResponse,
    JobListResponse,
    JobResponse,
    UploadInfo,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse, status_code=201)
def create_job(
    req: CreateJobRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreateJobResponse:
    """Create a job and assign an idle node.

    Returns job_id, status, and upload details (url, token, expires_at).
    """
    # Extract api_key_id from request.state (set by get_current_user)
    api_key_id = getattr(request.state, "api_key_id", None)

    job, upload_token = service.create_job(
        db=db,
        settings=settings,
        user=user,
        api_key_id=api_key_id,
        original_filename=req.original_filename,
        file_size_bytes=req.file_size_bytes,
    )

    return CreateJobResponse(
        job_id=job.id,
        status=job.status,
        upload=UploadInfo(
            url=job.node_upload_url,
            token=upload_token,
            expires_at=job.upload_token_expires_at,
        ),
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Get a job by ID. User can only see own jobs."""
    job = service.get_job(db, job_id, user)
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """List all jobs for the authenticated user, newest first."""
    jobs = service.list_user_jobs(db, user.id)
    return JobListResponse(jobs=[JobResponse.model_validate(j) for j in jobs])
