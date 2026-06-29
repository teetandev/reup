#!/usr/bin/env bash
set -euo pipefail

# Reup Vietsub VPS Agent Uninstaller
# Usage: sudo bash uninstall-node.sh

echo "==> Reup Vietsub VPS Agent Uninstall"

if [[ $EUID -ne 0 ]]; then
  echo "Error: must run as root"
  exit 1
fi

echo "==> Stopping and disabling service..."
systemctl stop reup-agent.service 2>/dev/null || true
systemctl disable reup-agent.service 2>/dev/null || true
rm -f /etc/systemd/system/reup-agent.service
systemctl daemon-reload

echo "==> Removing files..."
rm -rf /opt/reup-agent
rm -rf /etc/reup-agent
rm -rf /var/lib/reup-agent

echo "==> Removing user..."
userdel reup-agent 2>/dev/null || true

echo "✓ Uninstall complete"
