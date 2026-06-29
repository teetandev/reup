# Node Operations Runbook

## Check agent health

```bash
curl http://localhost:8100/health
```

## View logs

```bash
journalctl -u reup-agent -f
```

## Restart agent

```bash
sudo systemctl restart reup-agent
```

## Check disk

```bash
df -h /var/lib/reup-agent
```

## Cleanup old jobs

```bash
sudo /opt/reup-agent/scripts/cleanup-node.sh
```

## Common Issues

### Node offline

Check:
```text
- service running?
- control API URL correct?
- node token correct?
- network reachable?
```

### Render failed

Check:
```text
- ffmpeg installed?
- enough disk?
- subtitle file valid?
- input video valid?
```
