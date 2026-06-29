# VPS Provisioning Specification

## Goal

Allow admin to turn a fresh Ubuntu VPS into a Reup Vietsub VPS Agent.

## Preferred MVP Method: Install Command

Admin dashboard generates:

```bash
curl -fsSL https://your-control-domain.com/install-node.sh | bash -s --   --node-id NODE_ID   --node-token NODE_TOKEN   --control-api-url https://control.example.com   --public-url https://node-1.example.com
```

Admin SSHs into VPS manually and runs the command.

## Why This Method First

```text
- No need to store VPS password
- Lower security risk
- Easier to debug
- Works with cheap VPS
- Works without a master provisioner server
```

## install-node.sh Requirements

Must:

```text
- verify Ubuntu
- install ffmpeg
- install python or docker
- create user reup-agent
- create /var/lib/reup-agent
- create /etc/reup-agent/.env
- install app files or pull release
- install systemd service
- start service
- print health check
```

Must not:

```text
- echo node token in logs after setup
- store admin password
- require interactive input
```

## Systemd Service

Path:

```text
/etc/systemd/system/reup-agent.service
```

User:

```text
reup-agent
```

Working directory:

```text
/opt/reup-agent
```

Data directory:

```text
/var/lib/reup-agent
```

## Environment

```env
NODE_ID=
NODE_TOKEN=
CONTROL_API_URL=
AGENT_PUBLIC_URL=
MAX_JOBS=1
MAX_FILE_MB=500
WORK_DIR=/var/lib/reup-agent/jobs
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
```

## Future Method: Admin Enters IP + Password

This is not MVP.

If implemented:

```text
1. Admin enters IP, SSH port, username, password.
2. Provisioner uses password once.
3. Provisioner installs SSH key.
4. Provisioner installs agent.
5. Password is discarded immediately.
6. Password is never stored in DB or logs.
```

## Provisioning States

```text
PROVISIONING
IDLE
ERROR
OFFLINE
DISABLED
```

## Health Check

After install:

```bash
curl http://localhost:8100/health
```

Expected:

```json
{
  "ok": true,
  "node_id": "...",
  "status": "IDLE"
}
```

## Cloudflare Tunnel Recommendation

For production browser upload, each node should have HTTPS public URL.

Recommended:

```text
https://node-1.yourdomain.com
https://node-2.yourdomain.com
```

Use Cloudflare Tunnel or Nginx + SSL.
