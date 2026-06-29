"""FastAPI auth dependencies: settings, admin guard, current user."""

from __future__ import annotations

import secrets
import uuid

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db.enums import UserRole, UserStatus
from ..db.models import User
from ..db.session import get_db
from ..errors import ApiError
from .tokens import decode_token


def settings_dep() -> Settings:
    """Provide the cached Settings as a dependency."""
    return get_settings()


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "Missing or malformed bearer token.")
    return auth[len("Bearer ") :].strip()


def require_admin(
    request: Request, settings: Settings = Depends(settings_dep)
) -> dict[str, str]:
    """Authorize an admin caller.

    Accepts either:
    - ``X-Admin-Secret`` header matching ``ADMIN_BOOTSTRAP_SECRET`` (bootstrap), or
    - a Bearer JWT whose ``role`` is ADMIN.
    """
    header_secret = request.headers.get("X-Admin-Secret")
    if header_secret is not None and secrets.compare_digest(
        header_secret, settings.admin_bootstrap_secret
    ):
        return {"type": "bootstrap"}

    payload = decode_token(_bearer_token(request), settings)
    if payload.get("role") != UserRole.ADMIN.value:
        raise ApiError(403, "FORBIDDEN", "Admin privileges are required.")
    return {"type": "jwt", "sub": str(payload.get("sub"))}


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> User:
    """Resolve the authenticated user from a Bearer JWT.

    Also stores api_key_id in request.state if present in the token.
    """
    payload = decode_token(_bearer_token(request), settings)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc:
        raise ApiError(401, "UNAUTHORIZED", "Invalid token subject.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "User no longer exists.")
    if user.status != UserStatus.ACTIVE:
        raise ApiError(403, "USER_BLOCKED", "This user is blocked.")

    # Store api_key_id in request state for later use
    if "api_key_id" in payload:
        try:
            request.state.api_key_id = uuid.UUID(str(payload["api_key_id"]))
        except (ValueError, TypeError):
            pass

    return user
