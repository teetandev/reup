"""Local migration runner for the Control API.

Usage (from apps/control-api):
    python scripts/migrate.py upgrade        # apply all migrations (default: head)
    python scripts/migrate.py downgrade -1   # roll back one revision
    python scripts/migrate.py current        # show current revision
    python scripts/migrate.py history        # show migration history
    python scripts/migrate.py sql            # render upgrade SQL without a DB (offline)

The DB URL comes from settings.database_url / DATABASE_URL (see migrations/env.py).
This is a thin wrapper around Alembic; you can also call `alembic ...` directly.
"""

from __future__ import annotations

import os
import sys

from alembic import command
from alembic.config import Config

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_ROOT = os.path.dirname(_HERE)  # apps/control-api


def _config() -> Config:
    cfg = Config(os.path.join(_APP_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(_APP_ROOT, "migrations"))
    return cfg


def main(argv: list[str]) -> int:
    action = argv[0] if argv else "upgrade"
    rest = argv[1:]
    cfg = _config()

    if action == "upgrade":
        command.upgrade(cfg, rest[0] if rest else "head")
    elif action == "downgrade":
        command.downgrade(cfg, rest[0] if rest else "-1")
    elif action == "current":
        command.current(cfg, verbose=True)
    elif action == "history":
        command.history(cfg, verbose=True)
    elif action == "sql":
        # Offline render: upgrade SQL printed to stdout, no DB connection.
        command.upgrade(cfg, rest[0] if rest else "head", sql=True)
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
