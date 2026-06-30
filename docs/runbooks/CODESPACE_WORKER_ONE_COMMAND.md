# Codespace Worker — One Command

1. Admin → **VPS Nodes** → **Tạo node agent**. Copy **NODE_ID** + **NODE_TOKEN** (shown once).
2. Open a new **Codespace** from this repo.
3. Run:
   ```bash
   bash scripts/setup-codespace-worker.sh
   ```
4. Paste NODE_ID / NODE_TOKEN / AGENT_PUBLIC_URL / GROQ_API_KEY / GEMINI_API_KEY when asked
   (token/keys are hidden, never printed).
5. The script: checks deps, creates venv, installs reqs, writes `.env`, starts uvicorn on
   `0.0.0.0:8100` in tmux (`reup-worker`), local+public health check, heartbeat check.

## Port 8100 (IMPORTANT)
Public URL: `https://<codespace>-8100.app.github.dev/health`. In the **PORTS** tab, port 8100
must be **Visibility = Public** and **Protocol = HTTP**. If protocol is HTTPS you get HTTP/2 502.
The script tries `gh codespace ports visibility 8100:public` automatically when `gh` is authed;
protocol must be set manually in the PORTS tab if needed.

## Verify
- `curl -i http://localhost:8100/health`
- `curl -i $AGENT_PUBLIC_URL/health`
- Admin → VPS Nodes shows the node **IDLE**.
