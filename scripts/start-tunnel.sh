#!/usr/bin/env bash
set -euo pipefail

# Starts a Cloudflare tunnel to expose local backend
cloudflared tunnel --url http://localhost:8000
