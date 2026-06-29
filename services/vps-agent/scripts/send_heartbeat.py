"""Send ONE heartbeat to the Control API, then exit (manual test for Phase 06).

Reads NODE_ID / NODE_TOKEN / CONTROL_API_URL from the environment / .env (via
the agent Settings). The node token is never printed. Run from
``services/vps-agent``::

    python scripts/send_heartbeat.py

Exit code 0 if the Control API accepted the heartbeat (2xx), 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app` importable when run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.heartbeat import build_payload, send_heartbeat_once  # noqa: E402
from app.state import init_node_state  # noqa: E402


def main() -> int:
    settings = get_settings()
    state = init_node_state(settings)

    # Show the payload (no secrets) so the operator can eyeball it.
    payload = build_payload(state, settings)
    print(f"Sending heartbeat to {settings.control_api_url.rstrip('/')}/nodes/heartbeat")
    print(f"Payload: {payload}")

    try:
        resp = send_heartbeat_once(state, settings)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1
    except Exception as exc:  # transport / connection errors
        print(f"[FAIL] Could not reach Control API: {exc}")
        return 1

    ok = 200 <= resp.status_code < 300
    print(f"[{'OK' if ok else 'FAIL'}] HTTP {resp.status_code}: {resp.text}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
