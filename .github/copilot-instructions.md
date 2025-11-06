# Kuro AI - Copilot Instructions

## Project Overview
Kuro is a **production-grade, multi-model AI chatbot** featuring intelligent model routing, semantic memory, and resilient fallback chains. The system dynamically selects between LLM providers (Groq, OpenRouter) based on intent classification, cost, latency, and quality metrics.

**Stack**: FastAPI + React/TypeScript | MongoDB + Pinecone | Groq LLaMA 3 70B + Google Gemini embeddings

## Architecture Philosophy

### Simplified 4-Model Routing System (v2.0)
The core innovation is **skill-based model selection** via `backend/routing/model_router_v2.py`:

**One Model Per Skill:**
- **Conversation**: `llama-3.3-70b-versatile` (Groq) - Fast, natural chat
- **Reasoning**: `deepseek-r1-distill-llama-70b` (Groq) - Complex problem-solving
- **Code**: `llama-3.1-8b-instant` (Groq) - Code generation & debugging
- **Summarization**: `mixtral-8x7b-32k` (Groq) - Long-context summarization

**Routing Priority:**
1. **Forced Override** - Developer/user can specify exact model
2. **Skill Mapping** - Intent or keyword patterns map to predetermined models (`SKILL_TO_MODEL` dict)
3. **Score-Based** - Optional experimental routing (env: `ENABLE_SCORE_ROUTING=true`)
4. **Default** - Falls back to conversation model

**Key Pattern**: `get_best_model()` returns `{chosen_model, source, reason, confidence, fallback_used}` - always include routing decision metadata for observability.

**Configuration**: Set via `ROUTING_STRATEGY=skill` in `.env` (default) or `ROUTING_STRATEGY=score` (experimental).

### Orchestration & Resilience
`backend/orchestration/llm_orchestrator.py` manages the execution flow:
- **Intent Classification** (`backend/routing/intent_classifier.py`) - Regex-based pattern matching (NOT ML-based for performance)
- **Skill Detection** (`backend/routing/model_router_v2.py`) - Keyword patterns map queries to skills
- **Circuit Breaker** (`backend/reliability/circuit_breaker.py`) - Prevents cascading failures by tracking model health
- **Fallback Chains** - Each model in `model_registry.yml` has simplified fallback list (max 2 backups)

**Critical**: Fallback chains are limited to 3 models total (primary + 2 backups) for faster recovery.

### Layered Memory Architecture
Memory system (`backend/memory/`) uses **progressive summarization** to maintain conversation context:
- **Short-Term** - Recent N raw message turns (sliding window)
- **Medium Summary** - Aggregated batches of short-term conversations
- **Long Summary** - Compressed narrative arc across sessions
- **Verbatim Facts** - Append-only immutable user facts extracted during summarization

Context assembly order (from `backend/memory/context_rehydrator.py`): Facts → Layered Summaries → Recent Turns. Token budgeting trims oldest summaries first, never touches facts.

## Development Workflows

### Local Development Commands (PowerShell)
```powershell
# Start both frontend + backend
.\dev-start.ps1

# Or individually:
.\scripts\start-local-backend.ps1  # Backend on :8000
cd frontend; npm run dev:local     # Frontend on :3000
```

**Environment Setup**: Backend requires `.env` with `GROQ_API_KEY`, `GEMINI_API_KEY`, `PINECONE_API_KEY`, `MONGODB_URI`, `CLERK_SECRET_KEY`. Frontend requires `VITE_API_BASE_URL`, `VITE_CLERK_PUBLISHABLE_KEY`.

### Testing Philosophy
Tests use `pytest` with minimal mocking. Key test files:
- `backend/test_routing_and_resilience.py` - Model routing + circuit breaker
- `backend/test_intent_and_orchestrator.py` - Intent detection + orchestration flow
- `backend/test_model_router_v2.py` - Rule-based routing + fallback chains
- `backend/test_memory_system.py` - Pinecone + Gemini embeddings

Run tests: `cd backend; pytest -v` (ensure `conftest.py` adds backend to sys.path)

## Project-Specific Conventions

### Import Patterns
Backend uses **relative imports from root** (NOT package-style):
```python
from memory.chat_manager import ChatManager
from routing.model_router import route_model
from orchestration.llm_orchestrator import execute_with_orchestration
```
`backend/conftest.py` adds backend dir to sys.path for test imports.

### Frontend Component Structure
Components use **shadcn/ui + Radix** primitives with custom Tailwind theme:
- `frontend/src/components/ChatBubble.tsx` - Message display with markdown rendering
- `frontend/src/components/ChatInput.tsx` - Auto-resize textarea with validation
- `frontend/src/components/Sidebar.tsx` - Session CRUD operations

**Animation**: Framer Motion via `use-performance.tsx` hook for reduced-motion-aware animations.

### Model Registry Schema
Add new models to `backend/config/model_registry.yml`:
```yaml
- id: provider/model-name          # Normalize with routing.model_config
  label: descriptive_label
  capabilities: [reasoning, long_context, fast]
  fallback: ["backup-model-1", "backup-model-2"]
  max_context_tokens: 16384
  avg_latency_ms: 1200
  quality_tier: high|medium|low
  cost_score: 1-5 (1=cheap, 5=expensive)
```

### Routing Rules Syntax
Two rule types in `model_registry.yml`:
1. **Intent Rules**: `intent: "casual_chat"` → `choose: "llama-3.1-8b-instant"`
2. **Condition Rules**: `condition: "context_tokens > 20000"` → `choose: "mixtral-8x7b-32k"`

Conditions support: `context_tokens`, `message_len_chars`, basic operators (`>`, `<`, `and`, `or`).

## Integration Points

### External Services
- **Groq**: Fastest inference for LLaMA models via `httpx` client in `backend/orchestration/groq_client.py`
- **OpenRouter**: Multi-provider access (GPT-4, Claude, etc.) via `backend/orchestration/openrouter_client.py`
- **Pinecone**: Vector storage using `pinecone` SDK, indexes managed per-user
- **MongoDB**: Motor async driver, collections: `sessions`, `memories`, `user_profiles`, `llm_calls`
- **Clerk**: Auth via React hooks (`useAuth`, `useUser`) + backend JWT verification

### Cross-Component Communication
**Frontend → Backend**: REST API with Clerk JWT in Authorization header. Key endpoints:
- `POST /chat` - Main chat with `{message, session_id, user_id}`
- `GET /sessions` - List user sessions
- `POST /admin/registry/reload` - Hot-reload model registry (requires `ADMIN_API_KEY`)

**Backend Internal**: `orchestrator.execute_with_orchestration()` is the main entry point, routes through intent classifier → model router → provider client → safety validator.

## Common Pitfalls

### Model Registry Issues
- **Symptom**: Model not found errors
- **Solution**: Use `normalize_model_id()` from `backend/config/model_config.py` - handles case/provider variations
- **Prevention**: Always reference models by normalized ID in code

### Memory Token Overflow
- **Symptom**: Context length errors from LLM providers
- **Solution**: `backend/memory/context_rehydrator.py` has token budgeting - but manual assembly can exceed limits
- **Prevention**: Call `rehydrate_context(max_tokens=target_limit)` instead of manual concatenation

### Circular Import Deadlocks
- **Symptom**: ImportError at runtime (not startup)
- **Solution**: Backend uses lazy imports inside functions (see `chatbot.py` lines with `from memory.user_profile import ...` inside route handlers)
- **Prevention**: Import heavy modules inside functions, especially for optional features

### Frontend Build Failures
- **Symptom**: Vite build succeeds locally but fails on Vercel
- **Solution**: Check `frontend/vercel.json` for build overrides, ensure TypeScript strict mode compliance
- **Prevention**: Run `npm run build:prod` locally before pushing

## Performance Optimization Patterns

### Backend Cold Start
- `RAG_INDEX_CHECK_INTERVAL=300` - Cache empty Pinecone index detection (avoids repeated checks)
- `SKILL_AUTO_RELOAD_DISABLED=1` - Disable skill file hot-reloading on serverless platforms

### Frontend Bundle Size
- Lazy load heavy components with `React.lazy()` + `Suspense`
- Use `useOptimizedAnimations()` hook to disable animations on slow connections
- Clerk components are tree-shakeable - only import needed hooks

## Debugging Tips
- Enable verbose routing logs: `LOG_RAW_CONTENT=true` in backend `.env`
- Check routing decisions: `backend/logs/routing_decisions.jsonl` (structured JSONL)
- Frontend API errors: Network tab + check CORS config in `backend/chatbot.py` origins list
- Model provider errors: Circuit breaker state via `GET /admin/circuit-breakers` (requires admin key)

## Resources
- Full routing logic: `docs/ROUTING_AND_SKILLS_GUIDE.md`
- Memory architecture: `docs/MEMORY_ARCHITECTURE.md`
- Orchestration flow: `docs/ORCHESTRATION.md`
- Deployment checklist: `docs/DEPLOYMENT.md`
