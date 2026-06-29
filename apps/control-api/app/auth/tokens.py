"""JWT access tokens (HS256) for authenticated users."""

from __future__ import annotations

import datetime as dt
from typing import Any

import jwt

from ..config import Settings
from ..errors import ApiError

_ALGORITHM = "HS256"


def create_access_token(subject: str, role: str, settings: Settings, api_key_id: str | None = None) -> str:
    """Create a signed JWT for ``subject`` (user id) with ``role`` and optional ``api_key_id``."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expires_minutes),
    }
    if api_key_id is not None:
        payload["api_key_id"] = str(api_key_id)
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a JWT, raising a structured 401 on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "UNAUTHORIZED", "Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "UNAUTHORIZED", "Invalid access token.") from exc
