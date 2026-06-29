# VPS Node Installation Scripts

Scripts for installing, updating, and managing Reup Vietsub VPS Agent nodes.

## Installation

The install script is served by the control API at `GET /install-node.sh` and referenced in the admin dashboard after node registration.

### install-node.sh

Installs the VPS agent on a fresh Ubuntu VPS.

**Usage:**

```bash
curl -fsSL https://control.yourdomain.com/install-node.sh | bash -s -- \
  --node-id NODE_ID \
  --node-token NODE_TOKEN \
  --control-api-url https://control.yourdomain.com \
  --public-url https://node-1.yourdomain.com
```

**What it does:**

1. Verifies Ubuntu OS
2. Installs system dependencies: `ffmpeg`, `python3`, `python3-venv`, `python3-pip`, `curl`, `git`
3. Creates `reup-agent` user if not exists
4. Creates directories: `/opt/reup-agent`, `/etc/reup-agent`, `/var/lib/reup-agent/jobs`
5. Installs agent code (git clone or from tarball if `REUP_AGENT_TARBALL` env var set)
6. Creates Python virtualenv at `/opt/reup-agent/venv`
7. Installs Python dependencies from `requirements.txt`
8. Writes `/etc/reup-agent/.env` with node configuration (mode 640)
9. Creates systemd service `/etc/systemd/system/reup-agent.service`
10. Enables and starts the service
11. Runs health check at `http://localhost:8100/health`

**Arguments:**

- `--node-id` (required): Unique node identifier
- `--node-token` (required): Authentication token from control API
- `--control-api-url` (required): Control API base URL
- `--public-url` (required): Public-facing URL for this node
- `--port` (optional): Agent port, default 8100

**Security:**

- Node token is NOT echoed after writing to `.env`
- `.env` file permissions: 640 (root:reup-agent)
- Agent runs as non-root user `reup-agent`
- Script does NOT store VPS password

**Idempotent:** Safe to re-run (will update existing installation)

## Updating

### update-node.sh

Updates the VPS agent code and dependencies.

**Usage:**

```bash
sudo bash update-node.sh
```

Or fetch from control API:

```bash
curl -fsSL https://control.yourdomain.com/update-node.sh | sudo bash
```

**What it does:**

1. Stops the agent service
2. Pulls latest code from git repository
3. Updates Python dependencies
4. Starts the service
5. Runs health check

## Uninstalling

### uninstall-node.sh

Completely removes the VPS agent.

**Usage:**

```bash
sudo bash uninstall-node.sh
```

Or fetch from control API:

```bash
curl -fsSL https://control.yourdomain.com/uninstall-node.sh | sudo bash
```

**What it does:**

1. Stops and disables the systemd service
2. Removes `/opt/reup-agent`
3. Removes `/etc/reup-agent`
4. Removes `/var/lib/reup-agent` (including all job data)
5. Deletes the `reup-agent` user

**Warning:** This deletes all job files. Ensure no active jobs before uninstalling.

## File Locations

After installation:

```
/opt/reup-agent/              Agent code and virtualenv
├── venv/                     Python virtualenv
├── app/                      FastAPI application
├── video_pipeline_package/   Video processing pipeline
└── requirements.txt

/etc/reup-agent/
└── .env                      Configuration (NODE_ID, NODE_TOKEN, etc.)

/var/lib/reup-agent/
└── jobs/                     Job working directories
    └── {job_id}/             Per-job folder with input/output

/etc/systemd/system/
└── reup-agent.service        Systemd unit file
```

## Service Management

```bash
# Check status
sudo systemctl status reup-agent

# View logs
sudo journalctl -u reup-agent -f

# Restart
sudo systemctl restart reup-agent

# Stop
sudo systemctl stop reup-agent

# Start
sudo systemctl start reup-agent

# Disable auto-start
sudo systemctl disable reup-agent

# Enable auto-start
sudo systemctl enable reup-agent
```

## Troubleshooting

### Service won't start

```bash
# Check recent logs
sudo journalctl -u reup-agent -n 100 --no-pager

# Check configuration
sudo cat /etc/reup-agent/.env

# Check permissions
ls -la /etc/reup-agent/.env
ls -la /var/lib/reup-agent

# Test manually
cd /opt/reup-agent
sudo -u reup-agent /opt/reup-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8100
```

### Node shows OFFLINE in admin dashboard

- Verify control API is reachable from VPS:
  ```bash
  curl https://control.yourdomain.com/health
  ```
- Verify NODE_TOKEN in `/etc/reup-agent/.env` is correct
- Check firewall allows outbound HTTPS

### FFmpeg not found

```bash
# Verify FFmpeg is installed
ffmpeg -version

# If not, install it
sudo apt-get update
sudo apt-get install -y ffmpeg
```

### Python dependencies missing

```bash
cd /opt/reup-agent
sudo -u reup-agent ./venv/bin/pip install -r requirements.txt
sudo systemctl restart reup-agent
```

## Development

To test the install script locally without running it on a VPS:

```bash
# Set environment variable to use local tarball instead of git clone
export REUP_AGENT_TARBALL=/path/to/reup-vietsub.tar.gz

# Create tarball from repo root
tar -czf reup-vietsub.tar.gz services/vps-agent packages/video-pipeline packages/shared

# Run install script
bash scripts/install-node.sh \
  --node-id test-node \
  --node-token ntkn_test_token \
  --control-api-url http://localhost:8000 \
  --public-url http://localhost:8100
```

## See Also

- [NODE_INSTALL.md](../docs/runbooks/NODE_INSTALL.md) — Complete installation runbook for admins
- [VPS_PROVISIONING.md](../docs/specs/VPS_PROVISIONING.md) — Provisioning specification
- [SECURITY_MODEL.md](../docs/specs/SECURITY_MODEL.md) — Security architecture
