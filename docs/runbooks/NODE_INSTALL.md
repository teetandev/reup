# VPS Node Installation Runbook

## Prerequisites

- Fresh Ubuntu VPS (20.04+ recommended)
- 2vCPU / 2GB RAM minimum
- Root or sudo access
- Public IP or domain with HTTPS (recommended for production)

## Step 1: Register Node in Admin Dashboard

1. Log in to admin dashboard as admin user
2. Navigate to **Admin → Nodes**
3. Click **Register New Node**
4. Fill in:
   - **Node ID**: unique identifier (e.g., `node-1`, `vps-sg-01`)
   - **Public URL**: HTTPS endpoint for this node (e.g., `https://node-1.yourdomain.com`)
   - **Location**: datacenter/region (optional)
5. Click **Register**
6. **Copy the install command immediately** — the token is shown only once

The install command looks like:

```bash
curl -fsSL https://control.yourdomain.com/install-node.sh | bash -s -- \
  --node-id node-1 \
  --node-token ntkn_xxxxxxxxxxxx \
  --control-api-url https://control.yourdomain.com \
  --public-url https://node-1.yourdomain.com
```

## Step 2: SSH into the VPS

```bash
ssh root@your-vps-ip
```

Or use your VPS provider's console.

## Step 3: Run the Install Command

Paste the install command copied from the admin dashboard:

```bash
curl -fsSL https://control.yourdomain.com/install-node.sh | bash -s -- \
  --node-id node-1 \
  --node-token ntkn_xxxxxxxxxxxx \
  --control-api-url https://control.yourdomain.com \
  --public-url https://node-1.yourdomain.com
```

The script will:
- Detect Ubuntu
- Install FFmpeg, Python 3, Git
- Create `reup-agent` user
- Install agent code
- Create virtualenv and install dependencies
- Write `/etc/reup-agent/.env` with node credentials
- Create systemd service `reup-agent.service`
- Start the service
- Run health check

Expected output:

```
==> Reup Vietsub VPS Agent Installer
    Node ID: node-1
    Control API: https://control.yourdomain.com
    Public URL: https://node-1.yourdomain.com
==> Installing system dependencies...
==> Creating reup-agent user...
==> Creating directories...
==> Installing VPS Agent code...
==> Creating Python virtualenv...
==> Installing Python dependencies...
==> Writing configuration...
==> Creating systemd service...
==> Starting service...
==> Health check...
✓ Agent is running
{
  "ok": true,
  "node_id": "node-1",
  "status": "IDLE"
}
==> Installation complete!
```

## Step 4: Verify in Admin Dashboard

1. Return to **Admin → Nodes**
2. Find your node in the list
3. Status should be **IDLE** (green)
4. Last heartbeat should be recent (< 1 minute ago)

If status is **OFFLINE**:
- Check service: `sudo systemctl status reup-agent`
- Check logs: `sudo journalctl -u reup-agent -n 50`
- Verify network connectivity from VPS to control API

## Step 5: Setup HTTPS (Production)

For production, the node's public URL must be HTTPS. Two options:

### Option A: Cloudflare Tunnel (Recommended)

1. Install `cloudflared` on the VPS
2. Create a tunnel: `cloudflared tunnel create node-1`
3. Route `node-1.yourdomain.com` to `http://localhost:8100`
4. Run tunnel: `cloudflared tunnel run node-1`
5. Make it a systemd service for auto-start

### Option B: Nginx + Let's Encrypt

1. Install Nginx and Certbot
2. Get SSL cert: `certbot --nginx -d node-1.yourdomain.com`
3. Configure Nginx to proxy to `http://localhost:8100`

## Management Commands

### Check Service Status

```bash
sudo systemctl status reup-agent
```

### View Logs

```bash
sudo journalctl -u reup-agent -f
```

### Restart Service

```bash
sudo systemctl restart reup-agent
```

### Stop Service

```bash
sudo systemctl stop reup-agent
```

### Update Agent

```bash
curl -fsSL https://control.yourdomain.com/update-node.sh | sudo bash
```

Or use local script:

```bash
sudo bash /path/to/update-node.sh
```

### Uninstall Agent

```bash
curl -fsSL https://control.yourdomain.com/uninstall-node.sh | sudo bash
```

Or use local script:

```bash
sudo bash /path/to/uninstall-node.sh
```

## Configuration

Config file: `/etc/reup-agent/.env`

```env
NODE_ID=node-1
NODE_TOKEN=ntkn_xxxxxxxxxxxx
CONTROL_API_URL=https://control.yourdomain.com
AGENT_PUBLIC_URL=https://node-1.yourdomain.com
AGENT_PORT=8100
MAX_JOBS=1
MAX_FILE_MB=500
WORK_DIR=/var/lib/reup-agent/jobs
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
```

**Do not share NODE_TOKEN** — treat it like a password.

After editing `.env`, restart the service:

```bash
sudo systemctl restart reup-agent
```

## File Locations

```
/opt/reup-agent/              Agent code and virtualenv
/etc/reup-agent/.env          Configuration (readable only by root + reup-agent)
/var/lib/reup-agent/jobs/     Job working directories
/etc/systemd/system/reup-agent.service   Systemd unit file
```

## Troubleshooting

### Service won't start

```bash
sudo journalctl -u reup-agent -n 100 --no-pager
```

Common issues:
- Missing Python dependencies: reinstall via `update-node.sh`
- Invalid `NODE_TOKEN`: check `/etc/reup-agent/.env`
- Port 8100 already in use: change `AGENT_PORT` in `.env`
- `WORK_DIR` not writable: check permissions on `/var/lib/reup-agent`

### Node shows OFFLINE in admin dashboard

- Verify control API URL is reachable from VPS:
  ```bash
  curl https://control.yourdomain.com/health
  ```
- Check node token is correct in `/etc/reup-agent/.env`
- Check firewall rules (outbound HTTPS should be allowed)

### Job fails during processing

- Check disk space: `df -h /var/lib/reup-agent`
- Check FFmpeg: `ffmpeg -version`
- Check job logs in `/var/lib/reup-agent/jobs/{job_id}/`
- Check agent logs: `sudo journalctl -u reup-agent -n 200`

### Upload fails with 413 or 400

- Verify file size < 500MB
- Verify upload token is valid and not expired
- Check agent logs for rejection reason

## Security Notes

- **NODE_TOKEN** is stored in `/etc/reup-agent/.env` with mode `640` (root + reup-agent only)
- Agent runs as non-root user `reup-agent`
- Job files are isolated under `/var/lib/reup-agent/jobs/{job_id}/`
- Install script does **not** store VPS password
- Do **not** commit `.env` files to Git
- Rotate node token if compromised: delete and re-register node

## Next Steps

After installation:
1. Test with a sample video upload via web UI
2. Monitor first job in admin dashboard
3. Check output quality
4. Add more nodes as needed
5. Setup monitoring/alerts for node health
