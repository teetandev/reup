#!/usr/bin/env bash
set -euo pipefail

# Reup Vietsub VPS Agent Updater
# Usage: sudo bash update-node.sh

echo "==> Reup Vietsub VPS Agent Update"

if [[ $EUID -ne 0 ]]; then
  echo "Error: must run as root"
  exit 1
fi

if ! systemctl is-active --quiet reup-agent.service; then
  echo "Error: reup-agent service is not running"
  exit 1
fi

echo "==> Stopping service..."
systemctl stop reup-agent.service

echo "==> Updating agent code..."
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

git clone --depth 1 https://github.com/your-org/reup-vietsub.git "$TEMP_DIR"
sudo -u reup-agent cp -r "$TEMP_DIR/services/vps-agent/"* /opt/reup-agent/
sudo -u reup-agent cp -r "$TEMP_DIR/packages/video-pipeline" /opt/reup-agent/video_pipeline_package
sudo -u reup-agent cp -r "$TEMP_DIR/packages/shared" /opt/reup-agent/shared_package

echo "==> Updating dependencies..."
sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet --upgrade pip
sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet -r /opt/reup-agent/requirements.txt
sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet -e /opt/reup-agent/video_pipeline_package
sudo -u reup-agent /opt/reup-agent/venv/bin/pip install --quiet -e /opt/reup-agent/shared_package

echo "==> Starting service..."
systemctl start reup-agent.service

echo "==> Health check..."
sleep 3
if curl -sf http://localhost:8100/health > /dev/null; then
  echo "✓ Update complete"
else
  echo "✗ Health check failed"
  journalctl -u reup-agent.service -n 20 --no-pager
  exit 1
fi
