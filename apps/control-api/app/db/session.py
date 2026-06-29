"""Database engine and session factory.

The engine is created from ``settings.database_url``. If unset, the engine is
``None`` so the app can still start (e.g. health checks) without a database;
``get_db`` then raises a clear error.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings


def _make_engine() -> Engine | None:
    url = get_settings().database_url
    if not url:
        return None
    return create_engine(url, pool_pre_ping=True, future=True)


engine: Engine | None = _make_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a DB session (used from later phases)."""
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
