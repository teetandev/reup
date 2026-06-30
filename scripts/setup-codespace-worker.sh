#!/bin/bash
set -euo pipefail

# scripts/setup-codespace-worker.sh
# One-command setup for Reup Codespace Worker.

echo "======================================================================"
echo " NEW CODESPACE WORKER SETUP"
echo "======================================================================"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DIR="$REPO_ROOT/services/vps-agent"
VENV="$AGENT_DIR/.venv"
ENV_FILE="$AGENT_DIR/.env"
WORK_DIR="$REPO_ROOT/.worker/jobs"

# 1. Install/check dependencies
echo -e "\n==> Checking dependencies..."
MISSING_PKGS=""
if ! command -v python3 &> /dev/null; then MISSING_PKGS="python3 $MISSING_PKGS"; fi
if ! command -v ffmpeg &> /dev/null; then MISSING_PKGS="ffmpeg $MISSING_PKGS"; fi
if ! command -v ffprobe &> /dev/null; then MISSING_PKGS="ffprobe $MISSING_PKGS"; fi
if ! command -v tmux &> /dev/null; then MISSING_PKGS="tmux $MISSING_PKGS"; fi
if ! command -v curl &> /dev/null; then MISSING_PKGS="curl $MISSING_PKGS"; fi

if [ -n "$MISSING_PKGS" ]; then
    echo "    Missing dependencies: $MISSING_PKGS"
    echo "    Installing..."
    sudo apt update && sudo apt install -y ffmpeg python3-venv tmux curl
else
    echo "    All system dependencies are installed."
fi

# 2. Setup Python environment
echo -e "\n==> Setting up Python venv..."
mkdir -p "$WORK_DIR"
cd "$AGENT_DIR"
if [ ! -d "$VENV" ]; then
    python3 -m venv .venv
fi
# Using a small sub-script to avoid set -u issues with activate script
bash -c "
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
"
cd "$REPO_ROOT"

# 3. Detect AGENT_PUBLIC_URL
echo -e "\n==> Detecting Codespace environment..."
if [ -n "${CODESPACE_NAME:-}" ] && [ -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]; then
    AGENT_PUBLIC_URL="https://${CODESPACE_NAME}-8100.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "    Detected AGENT_PUBLIC_URL: $AGENT_PUBLIC_URL"
else
    echo "    Could not auto-detect Codespace URL."
    read -p "    Please enter AGENT_PUBLIC_URL (e.g. https://<name>-8100.app.github.dev): " AGENT_PUBLIC_URL
fi

NODE_ID="codespace-worker-01"

# 4. Prompt user for registration
echo -e "\n======================================================================"
echo " ACTION REQUIRED: REGISTER NODE IN ADMIN DASHBOARD"
echo "======================================================================"
echo " 1. Go to your Reup Web Admin -> VPS Nodes"
echo " 2. Click 'Register New Node'"
echo " 3. Enter exactly:"
echo "      Name:       $NODE_ID"
echo "      Public URL: $AGENT_PUBLIC_URL"
echo " 4. Save and copy the generated NODE_TOKEN."
echo ""
read -p " Do you already have the NODE_TOKEN from Admin? [y/N] " HAS_TOKEN

if [[ ! "$HAS_TOKEN" =~ ^[Yy]$ ]]; then
    echo -e "\n==> Setup paused."
    echo "    Please register the node first using the URL above."
    echo "    Then rerun this command: bash scripts/setup-codespace-worker.sh"
    echo "    Don't forget to set Port 8100 to PUBLIC in the Ports tab!"
    exit 0
fi

# 5. Ask for NODE_TOKEN
echo ""
read -s -p " Paste NODE_TOKEN: " NODE_TOKEN
echo ""

if [ -z "$NODE_TOKEN" ]; then
    echo "[ERROR] NODE_TOKEN cannot be empty."
    exit 1
fi

# 6. Write services/vps-agent/.env
echo -e "\n==> Writing .env configuration..."
cat > "$ENV_FILE" <<EOF
APP_ENV=development
NODE_ID=$NODE_ID
NODE_TOKEN=$NODE_TOKEN
CONTROL_API_URL=https://reup-control-api.onrender.com
AGENT_PUBLIC_URL=$AGENT_PUBLIC_URL
AGENT_PORT=8100
HEARTBEAT_INTERVAL_SECONDS=30
MAX_JOBS=1
MAX_FILE_MB=500
WORK_DIR=$WORK_DIR
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
FFMPEG_THREADS=3
FFMPEG_PRESET=ultrafast
FFMPEG_CRF=28
MOCK_AI=true
EOF

# 7. Start worker in tmux
echo "==> Starting VPS Agent in background (tmux)..."
SESSION="reup-worker"
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "    Killing existing tmux session: $SESSION"
    tmux kill-session -t "$SESSION"
fi

cd "$AGENT_DIR"
tmux new-session -d -s "$SESSION" -c "$AGENT_DIR" \
    "source $VENV/bin/activate && set -a && source $ENV_FILE && set +a && exec uvicorn app.main:app --host 0.0.0.0 --port 8100"
cd "$REPO_ROOT"

echo "    Waiting for uvicorn to boot (3s)..."
sleep 3

# 8. Test /health
echo "==> Testing local health endpoint..."
if curl -sf http://localhost:8100/health > /dev/null; then
    echo "    [OK] Local /health is responding."
else
    echo "    [WARN] Local /health did not respond immediately."
fi

echo "==> Testing public health endpoint..."
if curl -sf "$AGENT_PUBLIC_URL/health" > /dev/null; then
    echo "    [OK] Public /health is responding."
else
    echo "    [WARN] Public /health failed."
    echo "           Make sure you set Port 8100 to PUBLIC in the Ports tab!"
fi

# 9. Print final status
echo -e "\n======================================================================"
echo " WORKER READY!"
echo "======================================================================"
echo " NODE_ID         : $NODE_ID"
echo " AGENT_PUBLIC_URL: $AGENT_PUBLIC_URL"
echo ""
echo " Check Admin -> VPS Nodes. The node should become IDLE (online)"
echo " after the first heartbeat (within 30 seconds)."
echo ""
echo " Next Steps:"
echo "  1. Verify Port 8100 is Public in the 'Ports' panel."
echo "  2. Go to the Web UI and upload a video."
echo ""
echo " To view worker logs:"
echo "  tmux attach -t reup-worker"
echo "  (Press Ctrl+B, then D to detach)"
echo "======================================================================"
