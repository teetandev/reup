"""Structured error model for the VPS Agent.

Every error response follows the envelope defined in docs/specs/API_CONTRACT.md
and docs/specs/ERROR_MODEL.md::

    {
      "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": {}
      }
    }
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_config import get_logger

logger = get_logger(__name__)


class AgentError(Exception):
    """Raise to return a structured error response.

    Example::

        raise AgentError(409, "NODE_BUSY", "This node already has a job.")
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details: dict[str, Any] = details or {}


def error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the standard error envelope body."""
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _error_response(
    status_code: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_payload(code, message, details))


# Map common HTTP status codes to stable error codes (see ERROR_MODEL.md).
_HTTP_STATUS_CODE_MAP: dict[int, str] = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
    501: "NOT_IMPLEMENTED",
    503: "SERVICE_UNAVAILABLE",
}


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers so all errors return the standard envelope."""

    @app.exception_handler(AgentError)
    async def _handle_agent_error(_: Request, exc: AgentError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            422,
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Log the real cause server-side; never leak internals to the client.
        logger.exception("Unhandled exception: %s", exc)
        return _error_response(500, "INTERNAL_ERROR", "Internal server error.")
