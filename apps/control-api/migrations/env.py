"""Alembic environment for the Control API.

Loads target metadata from the app's models and the DB URL from settings/env.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the `app` package importable (apps/control-api on sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db import models  # noqa: E402,F401  (import registers tables on Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Default keeps offline `--sql` rendering working even without a configured .env.
_FALLBACK_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/reup_vietsub"


def _get_url() -> str:
    return get_settings().database_url or os.environ.get("DATABASE_URL") or _FALLBACK_URL


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Escape % to %% because Alembic uses configparser which treats % as interpolation syntax
    safe_url = _get_url().replace("%", "%%")
    config.set_main_option("sqlalchemy.url", safe_url)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
