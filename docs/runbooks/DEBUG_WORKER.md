# Debug: Worker

- Local health:  `curl -i http://localhost:8100/health`
- Public health: `curl -i $AGENT_PUBLIC_URL/health` (502 ⇒ set port Protocol=HTTP)
- Logs:    `tmux capture-pane -t reup-worker -p | tail -100`
- Attach:  `tmux attach -t reup-worker`
- Restart: `tmux kill-session -t reup-worker; bash scripts/setup-codespace-worker.sh`
- Check `.env` keys present (masked): `grep -c KEY services/vps-agent/.env`
- PYTHONPATH must include packages/video-pipeline + services/vps-agent.
- Heartbeat: look for "Heartbeat ok" / status 200 in logs.
