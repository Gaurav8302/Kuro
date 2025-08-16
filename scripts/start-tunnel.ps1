# Starts a Cloudflare tunnel to expose local backend
# Usage: ./scripts/start-tunnel.ps1

cloudflared tunnel --url http://localhost:8000
