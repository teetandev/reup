#!/usr/bin/env bash
set -euo pipefail

# Reup Vietsub VPS Agent Installer
# Usage: curl -fsSL https://control.example.com/install-node.sh | bash -s -- \
#   --node-id NODE_ID --node-token NODE_TOKEN \
#   --control-api-url https://control.example.com \
#   --public-url https://node-1.example.com

NODE_ID=""
NODE_TOKEN=""
CONTROL_API_URL=""
AGENT_PUBLIC_URL=""
AGENT_PORT="8100"

while [[ $# -gt 0 ]]; do
  case $1 in
    --node-id) NODE_ID="$2"; shift 2 ;;
    --node-token) NODE_TOKEN="$2"; shift 2 ;;
    --control-api-url) CONTROL_API_URL="$2"; shift 2 ;;
    --public-url) AGENT_PUBLIC_URL="$2"; shift 2 ;;
    --port) AGENT_PORT="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$NODE_ID" || -z "$NODE_TOKEN" || -z "$CONTROL_API_URL" || -z "$AGENT_PUBLIC_URL" ]]; then
  echo "Error: --node-id, --node-token, --control-api-url, --public-url required"
  exit 1
fi

echo "==> Reup Vietsub VPS Agent Installer"
echo "    Node ID: $NODE_ID"
echo "    Control API: $CONTROL_API_URL"
echo "    Public URL: $AGENT_PUBLIC_URL"

if ! grep -qi ubuntu /etc/os-release 2>/dev/null; then
  echo "Error: Ubuntu required"
  exit 1
fi

echo "==> Installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg python3 python3-venv python3-pip curl git > /dev/null

echo "==> Creating reup-agent user..."
if ! id -u reup-agent > /dev/null 2>&1; then
  sudo useradd -r -m -d /opt/reup-agent -s /bin/bash reup-agent
fi

echo "==> Creating directories..."
sudo mkdir -p /opt/reup-agent
sudo mkdir -p /etc/reup-agent
sudo mkdir -p /var/lib/reup-agent/jobs
sudo chown -R reup-agent:reup-agent /opt/reup-agent /var/lib/reup-agent

echo "==> Installing VPS Agent code..."
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

if [[ -n "${REUP_AGENT_TARBALL:-}" && -f "$REUP_AGENT_TARBALL" ]]; then
  sudo -u reup-agent tar -xzf "$REUP_AGENT_TARBALL" -C /opt/reup-agent --strip-components=1
else
  git clone --depth 1 https://github.com/your-org/reup-vietsub.git "$TEMP_DIR"
  sudo -u reup-agent cp -r "$TEMP_DIR/services/vps-agent/"* /opt/reup-agent/
  sudo -u reup-agent cp -r "$TEMP_DIR/packages/video-pipeline" /opt/reup-agent/video_pipeline_package
  sudo -u reup-agent cp -r "$TEMP_DIR/packages/shared" /opt/reup-agent/shared_package
fi

echo "==> Creating Python virtualenv..."
sudo -u reup-agent python3 -m venv /opt/reup-agent/venv
sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet --upgrade pip

echo "==> Installing Python dependencies..."
if [[ -f /opt/reup-agent/requirements.txt ]]; then
  sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet -r /opt/reup-agent/requirements.txt
fi
if [[ -d /opt/reup-agent/video_pipeline_package ]]; then
  sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet -e /opt/reup-agent/video_pipeline_package
fi
if [[ -d /opt/reup-agent/shared_package ]]; then
  sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet -e /opt/reup-agent/shared_package
fi

echo "==> Writing configuration..."
sudo tee /etc/reup-agent/.env > /dev/null <<EOF
NODE_ID=$NODE_ID
NODE_TOKEN=$NODE_TOKEN
CONTROL_API_URL=$CONTROL_API_URL
AGENT_PUBLIC_URL=$AGENT_PUBLIC_URL
AGENT_PORT=$AGENT_PORT
MAX_JOBS=1
MAX_FILE_MB=500
WORK_DIR=/var/lib/reup-agent/jobs
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
EOF

sudo chmod 640 /etc/reup-agent/.env
sudo chown root:reup-agent /etc/reup-agent/.env

echo "==> Creating systemd service..."
sudo tee /etc/systemd/system/reup-agent.service > /dev/null <<'EOF'
[Unit]
Description=Reup Vietsub VPS Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=reup-agent
Group=reup-agent
WorkingDirectory=/opt/reup-agent
EnvironmentFile=/etc/reup-agent/.env
ExecStart=/opt/reup-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${AGENT_PORT}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "==> Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable reup-agent.service
sudo systemctl restart reup-agent.service

echo "==> Waiting for service to start..."
sleep 3

echo "==> Health check..."
if curl -sf http://localhost:$AGENT_PORT/health > /dev/null; then
  echo "✓ Agent is running"
  curl -s http://localhost:$AGENT_PORT/health | python3 -m json.tool || true
else
  echo "✗ Health check failed"
  sudo journalctl -u reup-agent.service -n 20 --no-pager
  exit 1
fi

echo ""
echo "==> Installation complete!"
echo "    Service: sudo systemctl status reup-agent"
echo "    Logs:    sudo journalctl -u reup-agent -f"
echo "    Config:  /etc/reup-agent/.env"
