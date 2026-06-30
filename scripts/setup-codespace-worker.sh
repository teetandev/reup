#!/usr/bin/env bash
# =============================================================================
# Reup Vietsub — One-command Codespace worker setup
#
#   bash scripts/setup-codespace-worker.sh
#
# Idempotent: re-running updates .env and restarts the worker cleanly.
# Never prints NODE_TOKEN / GROQ_API_KEY / GEMINI_API_KEY.
# =============================================================================
set -euo pipefail

TMUX_SESSION="reup-worker"
PORT_DEFAULT=8100

say()  { printf '\033[1;36m▸ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
err()  { printf '\033[1;31m✗ %s\033[0m\n' "$*"; }
mask() { local v="$1"; [ -n "$v" ] && printf '%s…(%d chars)' "${v:0:4}" "${#v}" || printf '<empty>'; }

# ---------------------------------------------------------------- repo root --
if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  err "Not inside a git repo. Run this from within the cloned repo."
  exit 1
fi
cd "$REPO_ROOT"
say "Repo root: $REPO_ROOT"

AGENT_DIR="$REPO_ROOT/services/vps-agent"
PIPELINE_DIR="$REPO_ROOT/packages/video-pipeline"
ENV_FILE="$AGENT_DIR/.env"
VENV="$AGENT_DIR/.venv"

# ------------------------------------------------------------- dependencies --
say "Checking dependencies…"
need_install=()
for bin in python3 curl git; do
  command -v "$bin" >/dev/null 2>&1 || { err "Missing required: $bin"; exit 1; }
done
command -v ffmpeg >/dev/null 2>&1 || need_install+=(ffmpeg)
command -v tmux   >/dev/null 2>&1 || need_install+=(tmux)

if [ "${#need_install[@]}" -gt 0 ]; then
  warn "Missing: ${need_install[*]}"
  if command -v apt-get >/dev/null 2>&1; then
    say "Installing via apt-get…"
    sudo apt-get update -y && sudo apt-get install -y "${need_install[@]}" \
      || warn "apt-get install failed — install ${need_install[*]} manually."
  else
    warn "Please install manually: ${need_install[*]}"
  fi
fi
command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg present" || warn "ffmpeg still missing"
command -v tmux   >/dev/null 2>&1 && ok "tmux present"   || { err "tmux required to run the worker"; exit 1; }

# --------------------------------------------------------------------- venv --
say "Setting up venv…"
[ -d "$VENV" ] || python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$AGENT_DIR/requirements.txt"
[ -f "$PIPELINE_DIR/requirements.txt" ] && pip install --quiet -r "$PIPELINE_DIR/requirements.txt"
# Safety net for required runtime packages.
pip install --quiet fastapi "uvicorn[standard]" httpx python-multipart >/dev/null 2>&1 || true
ok "venv ready"

# --------------------------------------------------------------- gather input -
echo
say "Enter node configuration (token/keys are hidden and never printed):"
read -r -p "NODE_ID: " NODE_ID
read -r -s -p "NODE_TOKEN: " NODE_TOKEN; echo
read -r -p "CONTROL_API_URL [https://reup-control-api.onrender.com]: " CONTROL_API_URL
CONTROL_API_URL="${CONTROL_API_URL:-https://reup-control-api.onrender.com}"

# Auto-detect Codespace public URL for port 8100 if available.
DEFAULT_PUBLIC=""
if [ -n "${CODESPACE_NAME:-}" ] && [ -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]; then
  DEFAULT_PUBLIC="https://${CODESPACE_NAME}-${PORT_DEFAULT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
fi
read -r -p "AGENT_PUBLIC_URL [${DEFAULT_PUBLIC:-https://...-8100.app.github.dev}]: " AGENT_PUBLIC_URL
AGENT_PUBLIC_URL="${AGENT_PUBLIC_URL:-$DEFAULT_PUBLIC}"

read -r -p "MOCK_AI [false]: " MOCK_AI; MOCK_AI="${MOCK_AI:-false}"
GROQ_API_KEY=""; GEMINI_API_KEY=""
if [ "$MOCK_AI" != "true" ]; then
  read -r -s -p "GROQ_API_KEY: " GROQ_API_KEY; echo
  read -r -s -p "GEMINI_API_KEY: " GEMINI_API_KEY; echo
fi
read -r -p "GROQ_MODEL [whisper-large-v3]: " GROQ_MODEL; GROQ_MODEL="${GROQ_MODEL:-whisper-large-v3}"
read -r -p "GEMINI_MODEL [gemini-2.5-flash]: " GEMINI_MODEL; GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"
read -r -p "OUTPUT_TTL_HOURS [6]: " OUTPUT_TTL_HOURS; OUTPUT_TTL_HOURS="${OUTPUT_TTL_HOURS:-6}"
read -r -p "PORT [$PORT_DEFAULT]: " PORT; PORT="${PORT:-$PORT_DEFAULT}"
WORK_DIR="$AGENT_DIR/agent_work"

# ------------------------------------------------------------- write .env ----
say "Writing $ENV_FILE (secrets not echoed)…"
umask 077
cat > "$ENV_FILE" <<EOF
NODE_ID=$NODE_ID
NODE_TOKEN=$NODE_TOKEN
CONTROL_API_URL=$CONTROL_API_URL
AGENT_PUBLIC_URL=$AGENT_PUBLIC_URL
MOCK_AI=$MOCK_AI
GROQ_API_KEY=$GROQ_API_KEY
GROQ_MODEL=$GROQ_MODEL
GEMINI_API_KEY=$GEMINI_API_KEY
GEMINI_MODEL=$GEMINI_MODEL
OUTPUT_TTL_HOURS=$OUTPUT_TTL_HOURS
WORK_DIR=$WORK_DIR
PORT=$PORT
HEARTBEAT_INTERVAL_SECONDS=30
EOF
ok ".env written  (NODE_ID=$NODE_ID, NODE_TOKEN=$(mask "$NODE_TOKEN"), GROQ=$(mask "$GROQ_API_KEY"), GEMINI=$(mask "$GEMINI_API_KEY"))"

# ------------------------------------------------------------- start worker --
say "Starting worker (tmux session: $TMUX_SESSION)…"
tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || true
fuser -k "${PORT}/tcp" 2>/dev/null || true

PYTHONPATH_VAL="$PIPELINE_DIR:$AGENT_DIR"
START_CMD="cd '$AGENT_DIR' && source .venv/bin/activate && set -a && source .env && set +a && export PYTHONPATH='$PYTHONPATH_VAL:\$PYTHONPATH' && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"
tmux new-session -d -s "$TMUX_SESSION" "$START_CMD"
ok "tmux session started"

# ------------------------------------------------------------ local health --
say "Waiting for local health…"
LOCAL_OK="FAIL"
for _ in $(seq 1 15); do
  if curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1; then LOCAL_OK="OK"; break; fi
  sleep 1
done
if [ "$LOCAL_OK" = "OK" ]; then ok "Local health OK (http://localhost:$PORT/health)"; else
  err "Local health FAILED — last logs:"; tmux capture-pane -t "$TMUX_SESSION" -p 2>/dev/null | tail -30
fi

# --------------------------------------------------------- public port auto --
say "Configuring public port $PORT…"
if [ -n "${CODESPACE_NAME:-}" ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if gh codespace ports visibility "${PORT}:public" -c "$CODESPACE_NAME" >/dev/null 2>&1; then
    ok "Set port $PORT visibility=public via gh"
  else
    warn "gh could not set visibility automatically."
  fi
  warn "If public /health returns HTTP/2 502: open PORTS tab → port $PORT → Protocol = HTTP (not HTTPS)."
else
  warn "gh CLI not authenticated / not a Codespace — set the port manually:"
  echo "    Open PORTS tab → port $PORT → Visibility = Public, Protocol = HTTP"
fi

# ------------------------------------------------------------ public health --
PUBLIC_OK="SKIP"
if [ -n "$AGENT_PUBLIC_URL" ]; then
  say "Checking public health: $AGENT_PUBLIC_URL/health"
  if curl -fsS "$AGENT_PUBLIC_URL/health" >/dev/null 2>&1; then
    PUBLIC_OK="OK"; ok "Public health OK"
  else
    PUBLIC_OK="FAIL"; warn "Public health FAILED — ensure port $PORT is Public + Protocol HTTP (HTTPS causes 502)."
  fi
fi

# --------------------------------------------------------------- heartbeat ---
say "Waiting ~35s for heartbeat…"
sleep 35
HB_OK="FAIL"
if tmux capture-pane -t "$TMUX_SESSION" -p 2>/dev/null | grep -qiE "Heartbeat ok|heartbeat.*200"; then
  HB_OK="OK"; ok "Heartbeat OK"
elif tmux capture-pane -t "$TMUX_SESSION" -p 2>/dev/null | grep -qiE "Heartbeat loop started"; then
  HB_OK="STARTED"; warn "Heartbeat loop started (no explicit 200 yet) — check Admin for IDLE."
else
  warn "Heartbeat not confirmed in logs."
fi

# ------------------------------------------------------------------ summary --
echo
echo "──────────────── Setup summary ────────────────"
printf "  Local health   : %s\n" "$LOCAL_OK"
printf "  Public health  : %s\n" "$PUBLIC_OK"
printf "  Heartbeat      : %s\n" "$HB_OK"
printf "  Node ID        : %s\n" "$NODE_ID"
echo "  Attach logs    : tmux attach -t $TMUX_SESSION"
echo "  Tail logs      : tmux capture-pane -t $TMUX_SESSION -p | tail -100"
echo "  Stop worker    : tmux kill-session -t $TMUX_SESSION"
echo "────────────────────────────────────────────────"
[ "$LOCAL_OK" = "OK" ] && ok "Worker is running. Check Admin → VPS Nodes for IDLE status."
