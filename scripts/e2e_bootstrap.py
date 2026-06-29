"""E2E bootstrap — admin-side setup against a running Control API (Phase 15).

Run this AFTER the Control API is up and migrated, but BEFORE starting the VPS
agent (the agent needs the NODE_ID/NODE_TOKEN this script prints).

It performs the admin steps that require ADMIN_BOOTSTRAP_SECRET:
  1. Create a user
  2. Issue a secret key for that user      (shown once)
  3. Register a VPS node                    (node token shown once)

It then prints:
  - the user SECRET KEY  -> use it to log in / pass to scripts/e2e_run.py
  - the NODE_ID + NODE_TOKEN -> put them in services/vps-agent/.env, then start
    the agent so it heartbeats and the node flips to IDLE.

These are LOCAL-ONLY secrets surfaced once so you can wire up the agent. They are
never persisted by this script. Do not paste them into shared logs.

Usage (from repo root, any venv with httpx):
    python scripts/e2e_bootstrap.py \
        --control-api http://localhost:8000 \
        --admin-secret change-me \
        --node-public-url http://localhost:8100

Requires: pip install httpx
"""

from __future__ import annotations

import argparse
import sys

try:
    import httpx
except ImportError:  # pragma: no cover
    print("This script needs httpx:  pip install httpx", file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description="E2E admin bootstrap")
    ap.add_argument("--control-api", default="http://localhost:8000")
    ap.add_argument("--admin-secret", default="change-me")
    ap.add_argument("--display-name", default="E2E Test User")
    ap.add_argument("--node-name", default="local-node-1")
    ap.add_argument("--node-public-url", default="http://localhost:8100")
    args = ap.parse_args()

    base = args.control_api.rstrip("/")
    admin_headers = {"X-Admin-Secret": args.admin_secret}

    with httpx.Client(timeout=30.0) as c:
        # 0. sanity: control API is up
        h = c.get(f"{base}/health")
        h.raise_for_status()
        print(f"[ok] Control API healthy: {h.json()}")

        # 1. create user
        r = c.post(
            f"{base}/admin/users",
            headers=admin_headers,
            json={"display_name": args.display_name, "daily_job_limit": 100, "max_file_mb": 500},
        )
        if r.status_code >= 400:
            print(f"[fail] create user -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        user = r.json()
        user_id = user["id"]
        print(f"[ok] user created: id={user_id} role={user['role']}")

        # 2. issue secret key (shown once)
        r = c.post(
            f"{base}/admin/users/{user_id}/keys",
            headers=admin_headers,
            json={"name": "e2e-key"},
        )
        if r.status_code >= 400:
            print(f"[fail] issue key -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        secret_key = r.json()["secret_key"]
        print(f"[ok] secret key issued (prefix={r.json()['key_prefix']})")

        # 3. register node (node token shown once)
        r = c.post(
            f"{base}/admin/nodes",
            headers=admin_headers,
            json={"name": args.node_name, "public_url": args.node_public_url},
        )
        if r.status_code >= 400:
            print(f"[fail] register node -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        node = r.json()
        node_id = node["id"]
        node_token = node["node_token"]
        print(f"[ok] node registered: id={node_id} status={node['status']}")

    print("\n" + "=" * 70)
    print("LOCAL E2E SECRETS (shown once — wire these up, do not share):")
    print("=" * 70)
    print("\n# 1) Put these in services/vps-agent/.env, then start the agent:")
    print(f"NODE_ID={node_id}")
    print(f"NODE_TOKEN={node_token}")
    print(f"CONTROL_API_URL={base}")
    print(f"AGENT_PUBLIC_URL={args.node_public_url}")
    print("\n# 2) Use this secret key to run the user flow:")
    print(f"#   python scripts/e2e_run.py --control-api {base} --secret-key <KEY> [video.mp4]")
    print(f"SECRET_KEY={secret_key}")
    print("\nAfter the agent starts and heartbeats (~30s), the node flips to IDLE")
    print("and jobs can be scheduled. Check: GET /admin/nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
