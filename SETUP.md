# Kuro Backend: Local Dev + Cloudflare Tunnel

This guide sets you up to run the FastAPI backend locally, expose it safely using Cloudflare Tunnel, and wire the frontend (Vite on Vercel) to the correct API URL.

## Goals
- Run backend locally with `.env.local` for secrets.
- Expose backend with Cloudflare Tunnel when testing from Vercel.
- Ensure `.env.local` isn’t committed.
- Frontend points to the backend via `VITE_API_URL` (or `VITE_API_BASE_URL` fallback), using either:
  - `http://localhost:8000` (local dev), or
  - `https://your-tunnel.local.cloudflare.dev` (public testing)

---

## 1) Backend local env
Create `backend/.env.local` with your secrets (example):

```
# Backend local secrets
OPENAI_API_KEY=sk-xxxx
PINECONE_API_KEY=pc-xxxx
MONGODB_URI=mongodb://localhost:27017/kuro
GROQ_API_KEY=gr-xxxx
GEMINI_API_KEY=gm-xxxx
# Optional Whisper model
WHISPER_MODEL=gpt-4o-mini-transcribe
```

This repo now prefers `.env.local` and then falls back to `.env` automatically in `backend/chatbot.py`.

Run backend locally:

```powershell
# Windows PowerShell
cd backend
python -m pip install -r requirements.txt
uvicorn chatbot:app --reload --host 0.0.0.0 --port 8000
```

```bash
# macOS/Linux
cd backend
python3 -m pip install -r requirements.txt
uvicorn chatbot:app --reload --host 0.0.0.0 --port 8000
```

---

## 2) Git ignore
Ensure `.env.local` files aren’t committed. Add to `.gitignore` (root-level):

```
backend/.env.local
frontend/.env.local
```

---

## 3) Cloudflare Tunnel
Install cloudflared:

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared
# Linux
sudo apt-get update && sudo apt-get install cloudflared
# Windows (PowerShell)
winget install Cloudflare.cloudflared
```

Authenticate:

```bash
cloudflared tunnel login
```

Run a tunnel to your local backend:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the public URL, e.g. `https://kuro.local.cloudflare.dev`.

Optional helper scripts:

```powershell
# start-local-backend.ps1 (already in repo root)
# Starts uvicorn dev server

# start tunnel (Windows)
# Save as scripts/start-tunnel.ps1
cloudflared tunnel --url http://localhost:8000
```

```bash
# start-local-backend.sh (already in repo root)
# start tunnel (macOS/Linux)
# Save as scripts/start-tunnel.sh
cloudflared tunnel --url http://localhost:8000
```

---

## 4) Frontend wiring (Vite + Vercel)
Frontend reads the API base from `VITE_API_URL` or `VITE_API_BASE_URL` (see `frontend/src/lib/api.ts`).

Local dev (`frontend/.env.local`):

```
VITE_API_URL=http://localhost:8000
```

Vercel project env (Production/Preview):

```
VITE_API_URL=https://your-tunnel.local.cloudflare.dev
```

No code change needed; the existing Axios client uses `VITE_API_URL` -> `VITE_API_BASE_URL` -> default `http://localhost:8000`.

---

## 5) Dev workflow
- Local only: run backend (uvicorn) + frontend (vite dev). Frontend will hit localhost.
- Public testing: start Cloudflare tunnel; set Vercel env to the tunnel URL; frontend on Vercel talks to your local backend.
- Deploy: Frontend deploys on Vercel from GitHub; backend remains local (no Render).

---

## Copilot-ready prompt
Use this block to guide Copilot in VS Code:

````markdown
# Task for Copilot: Prepare Kuro Backend for Local Development + Cloudflare Tunnel Exposure

## Goals
1. Run FastAPI backend locally with `.env.local` for secrets.
2. Expose backend safely with **Cloudflare Tunnel** when testing from frontend on Vercel.
3. Ensure `.env` is ignored in git and documented.
4. Frontend (on Vercel) should call backend via env (`VITE_API_URL`) which points to either:
   - `http://localhost:8000` for local dev
   - Cloudflare Tunnel URL (e.g., `https://your-tunnel.local.cloudflare.dev`) for public testing

---

## Step 1: Local Backend Setup
- Add a `.env.local` file in backend root with API keys.
- Load `.env.local` in `chatbot.py` using `python-dotenv`:

  ```python
  from dotenv import load_dotenv
  load_dotenv('.env.local')
  load_dotenv()
  ```

- Run server locally:

  ```bash
  uvicorn chatbot:app --reload --host 0.0.0.0 --port 8000
  ```

---

## Step 2: Git Ignore

- Ensure `.env.local` is added to `.gitignore`:

  ```
  backend/.env.local
  frontend/.env.local
  ```

---

## Step 3: Cloudflare Tunnel

- Install cloudflared.
- Authenticate: `cloudflared tunnel login`
- Run: `cloudflared tunnel --url http://localhost:8000`
- Use the provided URL for `VITE_API_URL` on Vercel.

---

## Step 4: Frontend Connection (Vite)

- Local: `VITE_API_URL=http://localhost:8000` in `frontend/.env.local`.
- Vercel: `VITE_API_URL=https://your-tunnel.local.cloudflare.dev`.

---

## Step 5: Dev Workflow

- Local dev: backend + frontend.
- Public testing: start tunnel and point Vercel env to it.
- Deploy: frontend on Vercel, backend remains local.
````

---

Happy hacking!
