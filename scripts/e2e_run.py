"""E2E user flow — drive a full job through the live system (Phase 15).

Run this AFTER:
  - Control API is up + migrated,
  - scripts/e2e_bootstrap.py has created a user + key + node,
  - the VPS agent is running with the printed NODE_ID/NODE_TOKEN and has
    heartbeated (node is IDLE).

Steps performed (mirrors the browser flow in apps/web):
  1. login with the secret key                       -> JWT (never printed)
  2. POST /jobs                                       -> upload url + upload token
  3. upload the video directly to the VPS agent      (bytes never touch Control API)
  4. POST /jobs/{id}/start on the agent
  5. poll GET /jobs/{id} on Control API until terminal
  6. download the rendered MP4 from node_download_url

If no video path is given, a 10s test clip is generated with FFmpeg (testsrc +
sine). Combined with MOCK_AI=true on the agent, this gives a full offline E2E.

Secrets: the JWT and upload token are used but never logged (security rule).

Usage (from repo root, venv with httpx):
    python scripts/e2e_run.py --control-api http://localhost:8000 \
        --secret-key sub_live_xxx [path/to/video.mp4]

Requires: pip install httpx   (and ffmpeg on PATH if you don't pass a video)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

try:
    import httpx
except ImportError:  # pragma: no cover
    print("This script needs httpx:  pip install httpx", file=sys.stderr)
    raise SystemExit(2)

TERMINAL = {"DONE", "FAILED", "CANCELLED", "EXPIRED"}


def _make_sample(path: Path) -> None:
    """Create a tiny 10s test video with FFmpeg (color bars + tone)."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=10:size=320x240:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(path),
    ]
    print(f"[..] generating sample video with ffmpeg -> {path}")
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="E2E user flow")
    ap.add_argument("--control-api", default="http://localhost:8000")
    ap.add_argument("--secret-key", required=True)
    ap.add_argument("--poll-seconds", type=int, default=3)
    ap.add_argument("--timeout-seconds", type=int, default=1800)
    ap.add_argument("video", nargs="?", help="video file (auto-generated if omitted)")
    args = ap.parse_args()

    base = args.control_api.rstrip("/")

    # Resolve / generate the input video
    if args.video:
        video = Path(args.video)
        if not video.exists():
            print(f"[fail] video not found: {video}", file=sys.stderr)
            return 1
    else:
        video = Path("e2e_sample.mp4")
        if not video.exists():
            try:
                _make_sample(video)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                print(f"[fail] could not generate sample (need ffmpeg): {exc}", file=sys.stderr)
                return 1
    file_size = video.stat().st_size
    print(f"[ok] input video: {video} ({file_size} bytes)")

    with httpx.Client(timeout=60.0) as c:
        # 1. login
        r = c.post(f"{base}/auth/login", json={"secret_key": args.secret_key})
        if r.status_code >= 400:
            print(f"[fail] login -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        jwt = r.json()["access_token"]  # never printed
        auth = {"Authorization": f"Bearer {jwt}"}
        print(f"[ok] logged in as {r.json()['user']['display_name']}")

        # 2. create job
        r = c.post(
            f"{base}/jobs",
            headers=auth,
            json={"original_filename": video.name, "file_size_bytes": file_size},
        )
        if r.status_code >= 400:
            print(f"[fail] create job -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        data = r.json()
        job_id = str(data["job_id"])
        upload_url = data["upload"]["url"]
        upload_token = data["upload"]["token"]  # never printed
        print(f"[ok] job created: {job_id} status={data['status']}")

        # derive agent base from the upload url (scheme://host[:port])
        parts = urlsplit(upload_url)
        agent_base = f"{parts.scheme}://{parts.netloc}"

        # 3. upload directly to the agent
        with open(video, "rb") as fh:
            r = c.post(
                upload_url,
                headers={"Authorization": f"Bearer {upload_token}"},
                files={"file": (video.name, fh, "video/mp4")},
            )
        if r.status_code >= 400:
            print(f"[fail] upload -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        print(f"[ok] uploaded to agent: {r.json()}")

        # 4. start pipeline on the agent
        r = c.post(
            f"{agent_base}/jobs/{job_id}/start",
            headers={"Authorization": f"Bearer {upload_token}"},
        )
        if r.status_code >= 400:
            print(f"[fail] start -> {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        print(f"[ok] pipeline started: {r.json()}")

        # 5. poll Control API for status
        deadline = time.monotonic() + args.timeout_seconds
        last = None
        while time.monotonic() < deadline:
            r = c.get(f"{base}/jobs/{job_id}", headers=auth)
            if r.status_code >= 400:
                print(f"[fail] poll -> {r.status_code}: {r.text}", file=sys.stderr)
                return 1
            j = r.json()
            status = j["status"]
            if status != last:
                print(f"    status={status} progress={j.get('progress_percent')}% step={j.get('current_step')}")
                last = status
            if status in TERMINAL:
                break
            time.sleep(args.poll_seconds)
        else:
            print(f"[fail] timed out waiting for terminal status (last={last})", file=sys.stderr)
            return 1

        if status != "DONE":
            print(f"[fail] job ended {status}: code={j.get('error_code')} msg={j.get('error_message')}", file=sys.stderr)
            return 1

        # 6. download
        dl = j.get("node_download_url") or f"{agent_base}/jobs/{job_id}/download"
        out = Path(f"e2e_output_{job_id}.mp4")
        with c.stream("GET", dl) as resp:
            if resp.status_code >= 400:
                print(f"[fail] download -> {resp.status_code}", file=sys.stderr)
                return 1
            with open(out, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        print(f"[ok] downloaded output -> {out} ({out.stat().st_size} bytes)")

    print("\n[PASS] full E2E flow completed: login -> create -> upload -> render -> download")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
