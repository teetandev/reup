#!/bin/bash
# .devcontainer/postCreateCommand.sh
# Runs automatically after the Codespace container is created.
# Sets up the VPS Agent worker environment.

set -e

echo "==> [Reup Codespace] Post-create setup starting..."

# ── 1. System dependencies ──────────────────────────────────────────────────
echo "==> Installing system packages (ffmpeg, ffprobe)..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends ffmpeg curl tmux

# ── 2. Python venv for vps-agent ────────────────────────────────────────────
echo "==> Creating Python venv in services/vps-agent/.venv ..."
cd /workspaces/reup/services/vps-agent
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
deactivate

# ── 3. Create work directory ─────────────────────────────────────────────────
echo "==> Creating worker jobs directory at /workspaces/reup/.worker/jobs ..."
mkdir -p /workspaces/reup/.worker/jobs

# ── 4. Copy .env.example if .env missing ─────────────────────────────────────
if [ ! -f /workspaces/reup/services/vps-agent/.env ]; then
  echo "==> No .env found. Copying .env.example → .env (EDIT BEFORE STARTING)"
  cp /workspaces/reup/services/vps-agent/.env.example \
     /workspaces/reup/services/vps-agent/.env
fi

echo ""
echo "======================================================================"
echo " Reup Codespace Worker — Setup complete!"
echo "======================================================================"
echo " Next steps:"
echo "   1. Edit services/vps-agent/.env (NODE_TOKEN, CONTROL_API_URL, ...)"
echo "   2. Run:  bash scripts/start-codespace-worker.sh"
echo "   3. Set port 8100 to PUBLIC in the Ports panel"
echo "   4. Copy the https://<codespace>-8100.app.github.dev URL"
echo "   5. Register the node in Admin Dashboard"
echo "======================================================================"
