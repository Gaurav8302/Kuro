# Kuro — Maintenance Audit One

Date: 2026-09-21  
Scope: Restore chat, models, embeddings, error semantics, and dependency installability.  
Demo MongoDB / Pinecone data was authorized for deletion; live reset requires API credentials that were not present in this environment.

---

## Summary

Kuro’s live chat path was calling retired Groq model IDs and converting provider 404s into HTTP 200 assistant messages that were then persisted. This maintenance pass:

* Replaced retired Groq models with current production models (`openai/gpt-oss-120b` → primary, `openai/gpt-oss-20b` → fallback/fast).
* Centralized model IDs in `backend/config/active_models.py`.
* Made provider failures raise `LLMProviderError`, return HTTP errors, and **never** persist as assistant messages.
* Replaced `text-embedding-004` + 384-d slicing with `models/gemini-embedding-001` at **768** dimensions (normalized).
* Default Pinecone index name is now `kuro-memory` (clean 768-d index).
* Restored `backend/requirements.txt`.
* Added `backend/env.example` and `scripts/reset_demo_data.py` for clean demo resets when credentials are available.
* Added regression tests in `backend/tests/test_maintenance_audit_one.py`.

---

## Root Causes

1. Groq shut down `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, and earlier `deepseek-r1-distill-llama-70b` / Mixtral; Kuro still sent those IDs.
2. Fallback chains pointed at the same dead models (or unreachable OpenRouter IDs).
3. `llm/router.py` swallowed exceptions into a canned sentence; `POST /chat` treated that as success and saved it.
4. Embeddings used shut-down `text-embedding-004` and unsafe 384-d slicing.
5. `backend/requirements.txt` was missing, breaking clean installs / CI.

---

## Files Changed

| File | Reason |
| --- | --- |
| `backend/config/active_models.py` | **New** central primary/fallback model config + legacy remaps |
| `backend/config/embeddings.py` | **New** embedding model/dimension/index defaults |
| `backend/llm/errors.py` | **New** `LLMProviderError` |
| `backend/llm/router.py` | Raise on failure; use active models |
| `backend/utils/groq_client.py` | Primary→fallback only; no silent success; remap retired IDs |
| `backend/reliability/fallback_router.py` | Use active fallback |
| `backend/config/model_registry.yml` | Only current Groq models |
| `backend/config/model_config.py` | Flagship constants + normalization remaps |
| `backend/memory/chat_manager_v3.py` | Propagate provider errors; return model metadata |
| `backend/chatbot.py` | HTTP error semantics; no persist on failure; cleaner exception JSON |
| `backend/db/pinecone.py` | gemini-embedding-001 @ 768; dimension validation; no zero vectors |
| `backend/memory/ultra_lightweight_memory.py` | Same embedding path; no 384 slice |
| `backend/memory/long_term_memory.py` | Same embedding path |
| `backend/memory/chat_manager_v2.py` | Remap hardcoded retired IDs |
| `backend/routing/model_router.py` | SAFE_DEFAULT → active primary |
| `backend/routing/model_router_lightweight.py` | Same |
| `backend/routing/model_router_minimal.py` | Same |
| `backend/routing/model_router_v2.py` | Docs/constants remapped |
| `backend/routing/model_router_v3.py` | Active models + resolver |
| `backend/routing/response_verifier.py` | Default model remapped |
| `backend/requirements.txt` | **Restored** |
| `backend/env.example` | Documented env vars (no secrets) |
| `scripts/reset_demo_data.py` | **New** Mongo + Pinecone demo wipe / 768-d index ensure |
| `frontend/src/lib/api.ts` | Parse structured error responses |
| `backend/tests/test_maintenance_audit_one.py` | **New** regression tests |
| `backend/test_routing_and_resilience.py` | Updated expectations |
| `backend/test_improved_memory.py` | Updated model lock assertions |
| `backend/test_model_router_v2.py` | Updated forced-model assertion |
| `KURO_MAINTENANCE_AUDIT_ONE.md` | This report |

---

## Model Changes

| Role | Old | New |
| --- | --- | --- |
| Primary chat | `llama-3.3-70b-versatile` | `openai/gpt-oss-120b` |
| Fast / fallback / code | `llama-3.1-8b-instant` | `openai/gpt-oss-20b` |
| Reasoning | `deepseek-r1-distill-llama-70b` | `openai/gpt-oss-120b` |
| Summarization | `mixtral-8x7b-32k` | `openai/gpt-oss-120b` |

Source: [Groq Supported Models](https://console.groq.com/docs/models) (verified 2026-09-21).

Flow: Request → primary → on failure → fallback → on failure → `LLMProviderError` / HTTP error.

---

## Embedding Changes

| | Old | New |
| --- | --- | --- |
| Model | `models/text-embedding-004` | `models/gemini-embedding-001` |
| Dimension | 768 sliced to 384 (`[::2]`) | **768** via `output_dimensionality=768` + L2 normalize |
| Zero-vector fallback | Yes (dangerous) | Removed — fails clearly |
| Default index | `my-chatbot-memory` | `kuro-memory` |
| Metric | (assumed) | `cosine` |

---

## Database Reset

### MongoDB

**Not executed in this environment** — `MONGODB_URI` was not set.

Script ready: `scripts/reset_demo_data.py` clears demo collections in `chatbot_db`:
`chats`, `chat_sessions`, `session_titles`, `sessions`, `memories`, `memories_v3`, `llm_calls`, `user_profiles`, `users`.

### Pinecone

**Not executed in this environment** — `PINECONE_API_KEY` was not set.

Script creates/recreates index `kuro-memory` at dimension **768**, metric **cosine**, or wipes vectors if the index already matches. Old 384-d demo vectors are disposable and should not be reused.

---

## Error Handling

* `GroqClient.generate_content` tries primary then fallback; raises `LLMProviderError` if both fail.
* `LLMRouter.GenericModel.generate` raises `LLMProviderError` (never returns a fake assistant sentence).
* `POST /chat` catches `LLMProviderError`, returns HTTP 4xx/5xx with `{error, message, model}`, and **does not** call `save_chat_to_db`.
* Successful replies only are persisted (user + assistant together, existing schema).

---

## Tests

| Suite | Result |
| --- | --- |
| `tests/test_maintenance_audit_one.py` | PASS (10) |
| `tests/test_model_normalization.py` | PASS |
| `test_routing_and_resilience.py` | PASS |
| `test_model_router_v2.py` | PASS |
| `test_prompt_policy_regressions.py` | PASS |
| `test_time_sensitive_classifier.py` | PASS |
| `test_instrumentation_middleware.py` | PASS |
| **Total above** | **40 passed** |

### Not run (missing credentials)

* Live Groq chat completion
* Live Gemini embedding
* Live Pinecone upsert/query
* Live Mongo persistence against a real cluster
* Frontend start against a live backend
* `scripts/reset_demo_data.py` against real services

---

## Remaining Issues

1. **No API keys in this workspace** — cannot verify live chat/memory end-to-end or wipe remote demo data from here. Operator must set env vars and run `python scripts/reset_demo_data.py`, then smoke-test `POST /chat`.
2. **`groq/compound-mini` research** remains retired with no Groq replacement; research/`search_mode` is still not a working feature on ChatManagerV3.
3. **Clerk JWT is still not verified** on the backend (pre-existing; not part of this maintenance blocker).
4. **Legacy OpenRouter IDs** remain in `model_config.py` maps for unused paths; live path remaps/ignores them.
5. FastAPI `on_event` deprecation warnings remain (non-blocking).

---

## Future Work

* Run `scripts/reset_demo_data.py` in the real Render/local environment with secrets.
* Smoke-test primary + forced-fallback + dual-failure against live Groq.
* Re-enable research with a non-Compound search provider if needed.
* Add server-side Clerk verification.
* Collapse unused v2 routers after traffic is confirmed on v3.

---

## Audit Conclusion (operator checklist)

After deploying with secrets:

```bash
# backend/.env from env.example, then:
cd backend && pip install -r requirements.txt
python ../scripts/reset_demo_data.py
gunicorn chatbot:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

Confirm: chat 200 with real model text; provider failure → non-200 and no assistant row; memory upsert/query at 768-d.
