# Kuro AI — Project Onboarding

## Project Summary

Kuro AI is a production-grade, full-stack multi-model AI chatbot. It features intelligent model routing across 4 specialized LLMs, semantic memory with vector search, resilient fallback chains, and enterprise-grade security. Built as a microservices architecture with a FastAPI backend and React frontend.

- **Live Demo**: https://kuro-tau.vercel.app
- **Backend API**: https://kuro-ix1w.onrender.com
- **Repository**: https://github.com/Gaurav8302/Kuro
- **License**: MIT

## Goal

Provide a fast, reliable, and intelligent AI assistant that can handle conversation, reasoning, code generation, and summarization through specialized model routing — with semantic memory that persists across sessions.

## Technology Stack

**Frontend:**
- React 18, TypeScript 5.5, Vite 5
- TailwindCSS 3.4, shadcn/ui, Radix primitives
- Framer Motion, Three.js (3D components)
- TanStack React Query, React Context
- Clerk authentication

**Backend:**
- Python 3.11, FastAPI, Uvicorn/Gunicorn
- Groq (primary LLM provider)
- OpenRouter (fallback provider)
- Google Gemini text-embedding-004 (embeddings)

**Database:**
- MongoDB Atlas (chat history, sessions, user profiles)
- Pinecone (vector embeddings for semantic memory)

**Infrastructure:**
- Vercel (frontend deployment)
- Render (backend deployment)
- GitHub Actions (CI)

## Setup

### Install

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Run

```bash
# Backend (from kuro_ai root)
.\scripts\start-local-backend.ps1

# Frontend
cd frontend
npm run dev
```

### Test

```bash
# Backend
cd backend
python -m pytest

# Frontend
cd frontend
npm test
```

## Folder Structure

```
kuro_ai/
├── backend/           # FastAPI application
│   ├── chatbot.py     # Main entry point
│   ├── orchestrator.py# Pre-processing filter layer
│   ├── config/        # Model registry, config loader
│   ├── llm/           # LLM providers (Groq, OpenRouter, Gemini)
│   ├── memory/        # Memory management (3-layer)
│   ├── routing/       # Model routing, intent classification
│   ├── reliability/   # Circuit breakers, fallback chains
│   ├── skills/        # 30+ skill definitions
│   └── safety/        # Content filtering, guardrails
├── frontend/          # React + Vite app
│   ├── src/
│   │   ├── components/# UI components
│   │   ├── pages/     # Route pages
│   │   ├── hooks/     # Custom React hooks
│   │   └── contexts/  # Context providers
│   └── vite.config.ts
├── scripts/           # Development helper scripts
└── everything-claude-code/  # External CLI tooling
```

## Core Features

- **4-Model Routing**: Conversation (LLaMA 3.3 70B), Reasoning (DeepSeek R1), Code (LLaMA 3.1 8B), Summarization (Mixtral 8x7B)
- **3-Layer Memory**: Short-term (raw exchanges), Medium-term (summarized batches), Long-term (vector embeddings)
- **Circuit Breaker**: Automatic failure recovery with fallback chains
- **Skill Engine**: 30+ skills with keyword-based intent matching
- **Safety System**: Content filtering, hallucination detection, response quality scoring
- **Split-View Multitasking**: Side-by-side AI sessions
- **Holographic UI**: Custom design system with animations

## Current Status

Production release v1.4.0 (March 2026). Stable and deployed on Vercel + Render.

## Known Issues

- Cold start latency on Render free tier
- Pinecone index readiness delay on fresh deployments
- No offline mode support
- Speech-to-text not yet integrated

## Important Documents

- [architecture.md](architecture.md) — System architecture and data flow
- [decisions.md](decisions.md) — Architecture Decision Records
- [memory.md](memory.md) — Project memory and lessons learned
- [roadmap.md](roadmap.md) — Development roadmap
- [conventions.md](conventions.md) — Coding conventions
- [MEMORY_AND_AI_ARCHITECTURE.md](MEMORY_AND_AI_ARCHITECTURE.md) — Deep memory system docs
