#!/bin/bash
# scripts/start-codespace-worker.sh
# Starts the Reup VPS Agent inside a GitHub Codespace (or any Linux environment).
# Runs uvicorn in the foreground by default; use --bg to detach with tmux.
#
# Usage:
#   bash scripts/start-codespace-worker.sh          # foreground
#   bash scripts/start-codespace-worker.sh --bg     # background (tmux session: reup-worker)

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DIR="$REPO_ROOT/services/vps-agent"
VENV="$AGENT_DIR/.venv"
ENV_FILE="$AGENT_DIR/.env"
WORK_DIR="${WORK_DIR:-$REPO_ROOT/.worker/jobs}"
PORT="${AGENT_PORT:-8100}"
BG_MODE=false

# ── Parse args ──────────────────────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --bg) BG_MODE=true ;;
  esac
done

# ── Checks ───────────────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "[ERROR] $ENV_FILE not found."
  echo "        Copy .env.example to .env and fill in NODE_TOKEN, CONTROL_API_URL, AGENT_PUBLIC_URL."
  exit 1
fi

# Validate required vars
source "$ENV_FILE"
missing=()
[ -z "$NODE_ID" ]           && missing+=("NODE_ID")
[ -z "$NODE_TOKEN" ]        && missing+=("NODE_TOKEN")
[ -z "$CONTROL_API_URL" ]   && missing+=("CONTROL_API_URL")
[ -z "$AGENT_PUBLIC_URL" ]  && missing+=("AGENT_PUBLIC_URL")
if [ ${#missing[@]} -gt 0 ]; then
  echo "[ERROR] Missing required .env variables: ${missing[*]}"
  exit 1
fi

# ── Create venv if missing ───────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
  echo "==> Creating Python venv..."
  python3 -m venv "$VENV"
fi

# ── Install / update deps ────────────────────────────────────────────────────
echo "==> Installing/updating requirements..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$AGENT_DIR/requirements.txt"

# ── Ensure work dir ──────────────────────────────────────────────────────────
mkdir -p "$WORK_DIR"

# ── Print info ───────────────────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo " Reup Codespace Worker"
echo "======================================================================"
echo " NODE_ID        : $NODE_ID"
echo " AGENT_PUBLIC_URL: $AGENT_PUBLIC_URL"
echo " CONTROL_API_URL : $CONTROL_API_URL"
echo " PORT           : $PORT"
echo " WORK_DIR       : $WORK_DIR"
echo " MOCK_AI        : ${MOCK_AI:-false}"
echo "======================================================================"
echo ""

# ── Start uvicorn ─────────────────────────────────────────────────────────────
START_CMD="$VENV/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT"

if $BG_MODE; then
  if ! command -v tmux &>/dev/null; then
    echo "[ERROR] tmux not found. Install it or run without --bg."
    exit 1
  fi
  SESSION="reup-worker"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  tmux new-session -d -s "$SESSION" -c "$AGENT_DIR" \
    "source $VENV/bin/activate && set -a && source $ENV_FILE && set +a && $START_CMD"
  echo "==> Worker started in tmux session '$SESSION'."
  echo "    Attach:  tmux attach -t $SESSION"
  echo "    Logs:    tmux attach -t $SESSION  (then Ctrl+B, D to detach)"
else
  echo "==> Starting VPS Agent (foreground)..."
  cd "$AGENT_DIR"
  set -a
  source "$ENV_FILE"
  set +a
  exec "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$PORT"
fi
