#!/bin/bash
# scripts/check-codespace-worker.sh
# Checks the health and status of the running Codespace Worker.
# Works both inside the Codespace and from outside (if PUBLIC_URL is set).

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../services/vps-agent" && pwd)"
ENV_FILE="$AGENT_DIR/.env"

# ── Load env ─────────────────────────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

PORT="${AGENT_PORT:-8100}"
LOCAL_URL="http://localhost:$PORT"
PUBLIC_URL="${AGENT_PUBLIC_URL:-}"

echo "======================================================================"
echo " Reup Codespace Worker — Health Check"
echo "======================================================================"
echo " NODE_ID         : ${NODE_ID:-<not set>}"
echo " PORT            : $PORT"
echo " LOCAL_URL       : $LOCAL_URL"
echo " AGENT_PUBLIC_URL: ${PUBLIC_URL:-<not set>}"
echo "======================================================================"

# ── Check tmux session ────────────────────────────────────────────────────────
echo ""
if command -v tmux &>/dev/null; then
  if tmux has-session -t reup-worker 2>/dev/null; then
    echo "[OK]   tmux session 'reup-worker' is RUNNING"
  else
    echo "[WARN] tmux session 'reup-worker' not found (worker may be in foreground or stopped)"
  fi
fi

# ── Local health check ────────────────────────────────────────────────────────
echo ""
echo "==> GET $LOCAL_URL/health"
if curl -sf "$LOCAL_URL/health" --max-time 5 | python3 -m json.tool 2>/dev/null; then
  echo "[OK]   /health responded"
else
  echo "[FAIL] /health did not respond — is the worker running?"
fi

# ── Local status check ────────────────────────────────────────────────────────
echo ""
echo "==> GET $LOCAL_URL/status"
if curl -sf "$LOCAL_URL/status" --max-time 5 | python3 -m json.tool 2>/dev/null; then
  echo "[OK]   /status responded"
else
  echo "[FAIL] /status did not respond"
fi

# ── Public URL check (if set) ─────────────────────────────────────────────────
if [ -n "$PUBLIC_URL" ]; then
  echo ""
  echo "==> GET $PUBLIC_URL/health (via public URL)"
  if curl -sf "$PUBLIC_URL/health" --max-time 10 | python3 -m json.tool 2>/dev/null; then
    echo "[OK]   Public URL /health responded"
  else
    echo "[WARN] Public URL /health failed — is port 8100 set to PUBLIC in the Ports panel?"
  fi
fi

echo ""
echo "======================================================================"
echo " Done."
echo "======================================================================"
