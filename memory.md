# Kuro AI — Project Memory

## Purpose

Persistent knowledge learned during development of Kuro AI.

## Constraints

- **Offline not supported**: Requires active internet connection for API calls
- **No backend**: Render free tier spins down; cold start ~15s
- **API key dependent**: All providers require API keys
- **MongoDB + Pinecone**: Both databases needed for full functionality
- **Free tier limits**: Groq and OpenRouter have rate limits and concurrent request caps

## User Preferences

- TypeScript strict mode for frontend
- Python 3.11+ with type hints for backend
- Functional React components with hooks (no class components)
- shadcn/ui component library
- TailwindCSS for styling
- Conventional Commits for git messages

## Lessons Learned

### 2025-01-27: v1.0.0 Production Baseline
- **Issue**: Initial multi-model approach had too many models, causing routing complexity
- **Resolution**: Simplified to 4 flagship models with deterministic skill-based routing
- **Impact**: Faster response times, lower costs, easier debugging

### 2025-08-10: Memory v3 Migration
- **Issue**: Legacy memory system lacked progressive summarization and fact extraction
- **Resolution**: Implemented 3-layer memory with rolling summarization, verbatim fact store, and context rehydration
- **Impact**: Better long-term context retention, efficient token usage

### 2025-08-11: Skill Engine Overhaul
- **Issue**: Manual skill selection in UI was confusing and limited
- **Resolution**: Built 30+ skills with automatic keyword-based matching, cooldown gating, and debug mode
- **Impact**: Higher precision intent capture, reduced noise

### 2026-03-18: Frontend Performance
- **Issue**: Large initial bundle with Three.js and heavy dependencies
- **Resolution**: Implemented lazy loading, code splitting, and Suspense boundaries
- **Impact**: Reduced initial chunk size, faster page loads

## Rejected Approaches

### Score-Based Routing
- **Why rejected**: Added complexity with marginal benefit over deterministic skill mapping
- **Status**: Preserved as experimental toggle (`ENABLE_SCORE_ROUTING=false`)

### Ultra-Lightweight Memory
- **Why rejected**: Too lossy; lost important context for quality responses
- **Status**: Legacy code remains but unused; v3 memory manager is active

### Manual Skill Dropdown
- **Why rejected**: Users didn't know which skill to select; caused confusion
- **Status**: Removed in v1.4.0; skills now auto-detected

## Known Pitfalls

- **Pinecone index empty on fresh deploy**: First messages skip RAG until probe confirms readiness
- **pymongo vs motor version conflict**: Must keep pymongo <4.10 when using motor 3.6.0
- **Skill cooldown**: Rapid multi-turn queries may not re-trigger skills due to cooldown
- **SplitView state conflicts**: React state updater race conditions in SplitViewContext
- **Render memory limit**: 512MB RAM requires careful dependency management; avoid heavy ML libs

## Important Context

- The backend `chatbot.py` is the single FastAPI entry point (~1066 lines)
- The frontend uses Vite with path aliases (`@/` maps to `src/`)
- CORS allows the main domain + any `.vercel.app` preview domains
- Circuit breaker states persist to `backend/data/circuit_breaker.json`
- Model registry is YAML-based at `backend/config/model_registry.yml`
- `ROUTING_STRATEGY=skill` is the current active strategy; `score` is experimental
