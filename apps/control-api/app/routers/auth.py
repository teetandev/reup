"""Auth router — secret-key login + current user."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, settings_dep
from ..auth.keys import key_prefix, verify_key
from ..auth.tokens import create_access_token
from ..config import Settings
from ..db.enums import ApiKeyStatus, UserStatus
from ..db.models import ApiKey, User
from ..db.session import get_db
from ..errors import ApiError
from ..schemas.auth import LoginRequest, LoginResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> LoginResponse:
    """Validate a secret key and return a JWT.

    Errors: INVALID_SECRET_KEY (401), KEY_REVOKED (403), USER_BLOCKED (403).
    """
    secret = body.secret_key
    prefix = key_prefix(secret)

    candidates = (
        db.execute(select(ApiKey).where(ApiKey.key_prefix == prefix)).scalars().all()
    )
    matched: ApiKey | None = None
    for candidate in candidates:
        if verify_key(secret, candidate.key_hash):
            matched = candidate
            break

    if matched is None:
        raise ApiError(401, "INVALID_SECRET_KEY", "Invalid secret key.")
    if matched.status != ApiKeyStatus.ACTIVE:
        raise ApiError(403, "KEY_REVOKED", "This secret key has been revoked.")

    user = db.get(User, matched.user_id)
    if user is None:
        raise ApiError(401, "INVALID_SECRET_KEY", "Invalid secret key.")
    if user.status != UserStatus.ACTIVE:
        raise ApiError(403, "USER_BLOCKED", "This user is blocked.")

    matched.last_used_at = dt.datetime.now(dt.timezone.utc)
    db.commit()

    token = create_access_token(user.id, user.role.value, settings, api_key_id=str(matched.id))
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic(id=str(user.id), display_name=user.display_name, role=user.role.value),
    )


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """Return the authenticated user (from the Bearer JWT)."""
    return UserPublic(
        id=str(current_user.id),
        display_name=current_user.display_name,
        role=current_user.role.value,
    )
