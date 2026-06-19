# Kuro AI — Architecture

## Purpose

This document describes the Kuro AI system architecture. Any architectural change must be reflected here.

## System Overview

Kuro AI is a production-grade multi-model AI chatbot with a client-server microservices architecture. The frontend (React) communicates with the backend (FastAPI) via REST, which orchestrates model selection, memory retrieval, and response generation across multiple AI providers.

## Architecture Style

Client-Server with Modular Monolith backend.

- **Frontend**: Single-page application (React + Vite), deployed on Vercel
- **Backend**: Modular monolith (FastAPI), deployed on Render
- **Communication**: REST over HTTPS with Clerk JWT authentication

## Core Modules

### Backend Modules

| Module | Path | Purpose |
|--------|------|---------|
| **Orchestrator** | `backend/orchestrator.py` | Entry filter: intent classification, skill injection, context assembly |
| **Model Router** | `backend/routing/model_router_v2.py` | Selects best model per query based on skill mapping |
| **Memory Manager** | `backend/memory/chat_manager_v3.py` | 3-layer memory (short/medium/long-term) |
| **LLM Providers** | `backend/llm/providers/` | Groq, OpenRouter, Gemini abstraction layer |
| **Circuit Breaker** | `backend/reliability/circuit_breaker.py` | Failure tracking and automatic recovery |
| **Skill Engine** | `backend/skills/` | 30+ skills with registry and router |
| **Safety** | `backend/safety/guards.py` | Content filtering and response validation |

### Frontend Modules

| Module | Path | Purpose |
|--------|------|---------|
| **App** | `frontend/src/App.tsx` | Root component with routing and auth guards |
| **Chat** | `frontend/src/pages/Chat.tsx` | Main chat interface (lazy loaded) |
| **Components** | `frontend/src/components/` | UI components (shadcn/ui + custom) |
| **Contexts** | `frontend/src/contexts/` | SplitView, theme, auth contexts |
| **API Client** | `frontend/src/lib/api.ts` | Axios-based backend communication |

## Data Flow

```
User Action
→ Browser (React SPA)
→ Clerk Auth (JWT validation)
→ API Client (axios)
→ FastAPI Backend (chatbot.py)
  → Orchestrator (orchestrator.py)
    → Intent Classification (routing/intent_classifier.py)
    → Skill Injection (skills/router.py)
    → Context Assembly (memory/context_assembler.py)
    → Model Routing (routing/model_router_v2.py)
    → Circuit Breaker Check (reliability/circuit_breaker.py)
    → LLM Execution (llm/providers/groq.py or openrouter.py)
    → Response Verification (safety/guards.py)
→ JSON Response
→ React UI Rendering
→ Memory Update (async)
```

## State Management

- **Global State**: React Context (SplitViewContext, auth via Clerk)
- **Server State**: TanStack React Query (caching and refetching)
- **Backend State**: In-memory circuit breaker states + MongoDB persistence

## Storage

| Store | Technology | Purpose |
|-------|-----------|---------|
| Chat History | MongoDB | Raw message exchanges per session |
| Summaries | MongoDB | Compressed conversation batches |
| Sessions | MongoDB | Session metadata and titles |
| User Profiles | MongoDB | User preferences and settings |
| Vector Memory | Pinecone | Semantic search embeddings (384-dim) |
| Circuit Breaker | JSON file | Persisted failure counts |

## External Services

| Service | Purpose | Authentication |
|---------|---------|---------------|
| Groq | Primary LLM inference | API key |
| OpenRouter | Fallback LLM inference | API key |
| Google Gemini | Text embeddings | API key |
| Clerk | User authentication | Secret key + Publishable key |
| MongoDB Atlas | Document database | Connection string |
| Pinecone | Vector database | API key + index name |

## Security

- **Authentication**: Clerk JWT-based, social login support
- **Authorization**: Session isolation per user
- **CORS**: Restricted to frontend domain + Vercel preview domains
- **Content Safety**: Input sanitization, output filtering, hallucination detection
- **Secrets**: All API keys via environment variables, never committed

## Deployment

| Component | Platform | Build | Start |
|-----------|----------|-------|-------|
| Frontend | Vercel | `npm run build` | SPA served via Vercel |
| Backend | Render | `backend/build.sh` | `backend/start.sh` (gunicorn) |

## Known Technical Debt

- **Cold Start**: Render free tier spins down after inactivity (~15s cold start)
- **Memory Inefficiency**: Ultra-lightweight memory module (legacy) still present
- **Duplicate Routing Code**: Two versions of model_router, session_tracker exist
- **Missing Tests**: Frontend test suite not fully implemented
- **No E2E Tests**: End-to-end testing not yet set up
