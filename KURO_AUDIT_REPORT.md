# Kuro Audit Report

Audit date: 21 September 2026  
Scope: read-only diagnosis of the repository plus the Render logs supplied with this request.  
No code, dependencies, configuration, or data were changed.

Confidence labels used below: **CONFIRMED**, **LIKELY**, **POSSIBLE**, **UNKNOWN**.

---

## 1. Executive Summary

Kuro’s application shell is up. The frontend at `https://kuro-tau.vercel.app` can reach the API, CORS allows that origin, MongoDB connects, and session/history endpoints return HTTP 200. A chat turn also returns HTTP 200.

The chat itself does not. Every live model call in the supplied logs fails with:

`404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions`

That 404 is not a missing route. Groq’s chat-completions endpoint is still the documented URL. Groq returns 404 when the **model id** does not exist or the key cannot access it. The three ids exercised on this request were shut down by Groq before today:

| Model id used on the live path | Groq shutdown | Source |
| --- | --- | --- |
| `llama-3.1-8b-instant` | 16 August 2026 | [Groq deprecations](https://console.groq.com/docs/deprecations) |
| `llama-3.3-70b-versatile` | 16 August 2026 | same |
| `deepseek-r1-distill-llama-70b` | 2 October 2025 | same |

The live chat path (`POST /chat` → `ChatManagerV3` → `llm/router.py` → `utils/groq_client.py`) treats those failures as a successful reply. It returns a canned sentence, persists that sentence as the assistant message, and logs `model=v3_model`. The user sees a normal chat bubble, not an API error.

Memory, RAG, skills, web research, and the older v2 router are not what failed this request. They are either skipped, or they depend on the same dead Groq models and a Gemini embedding model that Google shut down on 14 January 2026 (`text-embedding-004`).

The architecture is salvageable. Basic chat does not require a rewrite. It requires replacing the retired Groq model ids on the live path, and stopping provider failures from being stored as successful answers. Memory and retrieval should be repaired after chat generation works, because they need a new embedding model and a re-index. Existing vectors are not compatible with a naive model swap.

---

## 2. Repository Architecture

Kuro is a split deployment:

- Frontend: Vite + React 18 + TypeScript, Clerk auth, deployed on Vercel (`frontend/`).
- Backend: FastAPI served by Gunicorn + `uvicorn.workers.UvicornWorker`, deployed on Render (`backend/chatbot.py`).
- Conversation store: MongoDB.
- Vector store: Pinecone, embeddings via the legacy `google-generativeai` SDK.
- Generation: Groq OpenAI-compatible chat completions. OpenRouter exists in code but is not on the live chat path.

There is not one architecture. There are several generations living side by side. Only one of them handles `POST /chat` today.

| Generation | Entry | Status |
| --- | --- | --- |
| Live v3 chat | `memory/chat_manager_v3.py` + `llm/router.py` | **Active.** This is what the logs executed. |
| Chat manager v2 | `memory/chat_manager_v2.py` | **Not on `POST /chat`.** Still imported by tests and by the `DISABLE_MEMORY_INIT=1` branch. |
| Legacy shim | `memory/chat_manager.py` | Re-exports v2. |
| Ultra-lightweight memory | `memory/ultra_lightweight_memory.py` | Still used by `/store-memory`, `/retrieve-memory`, and `/health`. |
| Long-term memory module | `memory/long_term_memory.py` | Used by v2, not by v3. |
| Routers | `routing/model_router.py`, `_v2`, `_v3`, `_lightweight`, `_minimal` | v1 `route_model` still runs inside `GroqClient` even when the caller already chose a model. v3 router is used by v2 chat, not by `ChatManagerV3`. |
| Skills | `skills/skill_manager.py` | Used by v2 and the orchestrator. Not called by `ChatManagerV3`. |
| Orchestrator | `orchestration/llm_orchestrator.py`, `orchestrator.py` | Optional import from v2. Not on the live path. |
| Retrieval package | `retrieval/` | Side pipeline around the ultra-lightweight manager. Not the v3 retriever. |

Top-level layout that matters:

```
backend/chatbot.py                 API
backend/llm/router.py              live model selection
backend/utils/groq_client.py       live provider client
backend/memory/chat_manager_v3.py  live chat orchestration
backend/memory/controller.py       memory-use decision
backend/memory/retriever.py        Pinecone retrieval + LLM rerank
backend/memory/updater.py          post-turn extraction
backend/db/pinecone.py             embed + upsert/query
backend/database/db.py             Mongo connection
backend/memory/chat_database.py    sessions and transcripts
backend/config/model_registry.yml  fallback registry used by GroqClient
backend/config/model_config.py     second, conflicting model map
frontend/src/lib/api.ts            HTTP client
frontend/src/hooks/use-chat-panel.ts  send/receive chat
```

`backend/requirements.txt` is **not in the repository**. `backend/build.sh`, root `package.json`, and `.github/workflows/ci.yml` all install it. `requirements-minimal.txt` and `requirements-enhanced.txt` exist and are not what those scripts install. **CONFIRMED** for the working tree. The running Render process already has packages installed, so this did not cause the 404. It will break the next clean build and CI.

---

## 3. Current Execution Flow

Actual request path for the logged `POST /chat`. This is not the v2 design described in comments inside `chat_endpoint`.

```
Browser (kuro-tau.vercel.app)
  → Clerk session (frontend only)
  → POST /chat { user_id, message, session_id, search_mode, skill }
  → chatbot.chat_endpoint
  → Mongo: last 20 turns for the session
  → ChatManagerV3.handle_chat
       1. _analyze_intent          FastModel  llama-3.1-8b-instant
       2. MemoryController.decide  same FastModel instance from init
       3. retrieve/rerank          only if the decision JSON says so
       4. PromptBuilder + style hints
       5. _generate_response       MainModel  llama-3.3-70b-versatile
       6. asyncio task: MemoryUpdater.process
            extract + score        MidModel   llama-3.3-70b-versatile
  → save_chat_to_db (even if the reply is the canned error)
  → HTTP 200 ChatResponse(model="v3_model", route_rule="v3_rule")
```

Inside every `GenericModel.generate` call:

```
GroqClient.generate_content(prompt, model_id=<router choice>)
  → route_model() still runs and logs "Rule match: intent='casual_chat' -> llama-3.3-70b-versatile"
  → model_id argument then overrides that choice
  → POST https://api.groq.com/openai/v1/chat/completions
  → on failure, reliability.fallback_router walks model_registry.yml
  → llm/router.py catches the exception and returns a fixed string
```

`search_mode` and `skill` are accepted by `ChatInput` and sent by the frontend. `ChatManagerV3.handle_chat` does not read them. **CONFIRMED.**

### What the supplied log actually did

Timestamps are the Render timestamps from 21 September 2026, about 04:46:22–04:46:26 UTC.

| Step | Evidence | Call |
| --- | --- | --- |
| Process healthy | Gunicorn listening, startup complete, Motor initialized | Not a startup failure |
| CORS allowed | `Origin allowed (exact match): https://kuro-tau.vercel.app` | Not a CORS failure |
| Sessions and profile | `GET /sessions/...`, `/has-name`, `/name`, `/intro-shown` all 200 | Mongo reads work |
| History | `GET /chat/<session>` 200 before and after the turn | Transcript store works |
| Intent LLM | Circuit failures 1, then `Error generating from model llama-3.1-8b-instant` | `ChatManagerV3._analyze_intent` |
| Memory decision LLM | Same model, failure count 2, second identical error | `MemoryController.decide` |
| Answer LLM | `Error generating from model llama-3.3-70b-versatile`, then `Chat response ... model=v3_model` | `_generate_response` |
| Persist error text | `Chat saved: ...` | `save_chat_to_db` |
| Extract memory LLM | Another `llama-3.3-70b-versatile` 404 after the 200 | `MemoryUpdater.extract_memory` |
| Client refresh | Second `GET /chat/<session>` 200 | Frontend history reload |

The rule-match line naming `llama-3.3-70b-versatile` appears even for the 8B calls because `GroqClient._select_model` always calls `route_model` before applying `model_id`. The model that was actually sent is the one named in `llm.router`’s error line.

Fallback order for `llama-3.1-8b-instant`, from `model_registry.yml`:

`llama-3.1-8b-instant` → `deepseek-r1-distill-llama-70b` → `llama-3.3-70b-versatile` → stop

`llama-3.3-70b-versatile` lists `moonshotai/kimi-dev-72b:free` as its fallback, but `choose_fallback` only returns ids that exist as registry entries. That OpenRouter id is not an entry, so the conversation model has **no working fallback**. **CONFIRMED** in `reliability/fallback_router.py` and `config/model_registry.yml`.

OpenRouter is never called on this path. A dead Groq model does not cross over to another provider.

---

## 4. Component-by-Component Audit

| Component | Path | Called by live chat? | Appears functional? |
| --- | --- | --- | --- |
| FastAPI app | `backend/chatbot.py` | Yes | Partially. Starts, routes, persists. Chat content is a swallowed provider error. |
| Chat manager v3 | `backend/memory/chat_manager_v3.py` | Yes | Partially. Control flow runs. Every LLM step failed in the log. |
| LLM router | `backend/llm/router.py` | Yes | Broken model ids. Swallows exceptions into a fake answer. |
| Groq client | `backend/utils/groq_client.py` | Yes | Client init works. Completions 404. Sync `requests` inside a thread. |
| Model registry | `backend/config/model_registry.yml` | Yes, for fallbacks | All four flagship ids are retired or their replacements are also retired. |
| Model config | `backend/config/model_config.py` | Indirectly, via other routers | Large stale map. Not the live selector, but tests and v2 depend on it. |
| Router v1 | `backend/routing/model_router.py` | Yes, inside GroqClient | Runs, then its choice is overridden. Log noise and extra work. |
| Router v3 | `backend/routing/model_router_v3.py` | No, not from ChatManagerV3 | Implemented, pointed at the same dead Groq ids, plus `groq/compound-mini`. |
| Memory controller | `backend/memory/controller.py` | Yes | Runs an LLM call that 404s, then falls through. Intent JSON never arrives, so retrieval is skipped. **LIKELY** for this log: no Pinecone query line appears. |
| Retriever | `backend/memory/retriever.py` | Only if decision says so | Code exists. Embedding backend is dead. Rerank needs a live mid model. |
| Updater | `backend/memory/updater.py` | Yes, background task | Ran and failed the extraction call. Empty JSON fallback means nothing new is stored. |
| Pinecone helper | `backend/db/pinecone.py` | When retrieval or upsert runs | Embed call targets a shut-down model and then truncates to 384 dims. |
| Mongo sessions | `backend/memory/chat_database.py`, `backend/database/db.py` | Yes | Working in this log. |
| Mongo memories v3 | `backend/db/mongo.py` | After a successful extraction | Not exercised successfully in this log. |
| Ultra-lightweight memory | `backend/memory/ultra_lightweight_memory.py` | Legacy memory routes and health | Separate Pinecone path, same dead embedding model. |
| Skills | `backend/skills/` | No | Prompt overlays only. No tool execution runtime. |
| Compound research | `backend/routing/compound_research.py` | No on v3 | `groq/compound-mini` shutdown date is 21 September 2026. |
| OpenRouter client | `backend/utils/openrouter_client.py` | No | Present. Not wired into `LLMRouter`. |
| Admin | `backend/admin/` | Separate router | API key check. Not part of chat. |
| Observability | `backend/observability/instrumentation_middleware.py` | Yes | Motor initialized. Every request, including `GET /ping`, is logged as `llm_request_complete`. |
| Frontend chat | `frontend/src/hooks/use-chat-panel.ts` | Yes | Contract matches enough to complete the round trip. Treats the canned reply as a normal assistant message. |
| Auth | Clerk on the frontend only | Partial | Backend does not verify the bearer token. |

---

## 5. Model / Provider Audit

Verified against Groq’s deprecation page on 21 September 2026: https://console.groq.com/docs/deprecations  
Embedding status verified against Google’s Gemini API changelog and embeddings docs: https://ai.google.dev/gemini-api/docs/changelog and https://ai.google.dev/gemini-api/docs/embeddings

Groq’s own recommended replacement for `llama-3.3-70b-versatile` included `qwen/qwen3.6-27b`. That id was itself shut down on **14 September 2026** in favor of `qwen/qwen3.8-27b`. Do not migrate to `qwen/qwen3.6-27b`.

| Id / provider | Where it is hardcoded | Status | Notes |
| --- | --- | --- | --- |
| `llama-3.1-8b-instant` | `llm/router.py` fast + code; `groq_client.py` default; `model_registry.yml`; `model_router_v3.py` | **REMOVED** (16 Aug 2026) | Groq replacement: `openai/gpt-oss-20b` |
| `llama-3.3-70b-versatile` | `llm/router.py` main/mid; registry; v3 map; README | **REMOVED** (16 Aug 2026) | Groq replacements: `openai/gpt-oss-120b` or `qwen/qwen3.8-27b` (not 3.6) |
| `deepseek-r1-distill-llama-70b` | registry reasoning; `llm/router.py` reasoning; v3 | **REMOVED** (2 Oct 2025) | Old replacement `llama-3.3-70b-versatile` is also gone |
| `mixtral-8x7b-32768` / `mixtral-8x7b-32k` | registry summarizer; `llm/router.py` summarization; Groq map | **REMOVED** (20 Mar 2025) | Listed replacements (`mistral-saba-24b`, Llama 3.3 70B) are also gone |
| `gemma2-9b-it` | `model_config.py`, Groq map | **REMOVED** (8 Oct 2025) | Replacement was `llama-3.1-8b-instant`, now also gone |
| `llama3-8b-8192`, `llama3-70b-8192` | Groq map aliases | **REMOVED** (30 Aug 2025) | Aliases point at models that were later removed |
| `qwen/qwen3-32b` | `model_config.py` as a Groq model | **REMOVED** from Groq (17 Jul 2026) | Replacement: `openai/gpt-oss-120b` |
| `groq/compound`, `groq/compound-mini` | `compound_research.py`, `model_router_v3.py` | **REMOVED** as of 21 Sep 2026 | Groq lists no replacement model id |
| `models/text-embedding-004` | `db/pinecone.py`, `ultra_lightweight_memory.py`, `long_term_memory.py` | **REMOVED** from Gemini API (14 Jan 2026) | Replacement: `gemini-embedding-001` (default 3072-d; 768 recommended reduced size). `gemini-embedding-2` is a different space and cannot be mixed |
| `moonshotai/kimi-dev-72b:free` | registry fallback, not a registry entry | **UNKNOWN** as an OpenRouter id; **not reachable** from the live fallback function | Dead end even if the id still exists |
| OpenRouter model ids in `model_config.py` (`deepseek/r1`, `google/gemini-2.0-flash-exp:free`, Claude 3.5, GPT-4 Turbo, and others) | legacy map | **UNKNOWN** individually; several free/exp ids are **LIKELY** gone | Not on the live path |
| Groq chat URL `https://api.groq.com/openai/v1/chat/completions` | `groq_client.py` | **VALID** | The URL is current. The model ids are not. |
| Pinecone SDK usage `Pinecone(api_key=...).Index(...)` | `db/pinecone.py` | **VALID BUT NEEDS CONFIGURATION** | SDK style matches current Pinecone client. Index name, dimension, and metric were not inspected in a live account. |
| MongoDB | `database/db.py` | **VALID** | Connected in the log. |
| Clerk | frontend | **VALID BUT NEEDS CONFIGURATION** | Frontend uses it. Backend ignores the token. |
| Speech, vision, Ollama, LM Studio | — | Not present as a live integration | No local model server in the chat path. |

`GroqClient` initializes successfully in the log, so `GROQ_API_KEY` is present and accepted far enough to build the client. The client does not call Groq during `__init__`. The 404 happens on completions, which is the model-id failure mode, not a missing key (a bad key is handled as 401). **CONFIRMED** by `groq_client.py` status handling and the log line `404 Client Error`.

Enterprise Groq accounts with a committed-spend contract were exempt from some of these shutdowns. Nothing in the repo or the 404s suggests this deployment is on that contract. **LIKELY** a normal developer/free key.

### Conflicting model sources of truth

The same role is defined differently in different files:

| Role | `llm/router.py` (live) | `model_registry.yml` | `model_router_v3.py` (not live) | `model_config.py` flagship |
| --- | --- | --- | --- | --- |
| Conversation | `llama-3.3-70b-versatile` | same | `llama-3.1-8b-instant` | `llama-3.3-70b-versatile` |
| Fast / router | `llama-3.1-8b-instant` | code model | `llama-3.1-8b-instant` | `llama-3.1-8b-instant` |
| Reasoning | `deepseek-r1-distill-llama-70b` | same | same | same |
| Summarization | `mixtral-8x7b-32k` | same | same | `mixtral-8x7b-32k` |

Fixing only `llm/router.py` restores the live path. The other files will still break v2, tests, and any later switch back to router v3.

---

## 6. Dependency Audit

### Backend

| File | Role | Finding |
| --- | --- | --- |
| `backend/requirements.txt` | What `build.sh`, CI, and root `package.json` install | **Missing from the repo.** CONFIRMED. |
| `backend/requirements-minimal.txt` | Not referenced by the build | Pins FastAPI 0.116.1, Uvicorn 0.35.0, pymongo 4.9.2, `google-generativeai==0.8.5`, `pinecone==7.3.0`, gunicorn 21.2.0, requests. No `httpx` pin, no explicit `pydantic`. |
| `backend/requirements-enhanced.txt` | Optional ML | `sentence-transformers`, `torch`, `scikit-learn`. Not used by the live path. `DISABLE_EMBEDDINGS` is set only in `start.sh`, and the Render log’s start command is not `start.sh`. |
| `backend/runtime.txt` | `python-3.11.9` | Matches CI (`3.11`). Consistent. |

The running process imports FastAPI, Gunicorn 21.2.0, pymongo, Motor, structlog or a fallback logger, and `google.generativeai` is imported at startup via `db/pinecone.py` and the ultra-lightweight manager. Those imports succeeded, so the deployed environment has them even though `requirements.txt` is absent here. **CONFIRMED** deployed-vs-repo drift.

`google-generativeai` 0.8.5 is the legacy SDK. Current Gemini embeddings docs describe `gemini-embedding-001` / `gemini-embedding-2`. Whether 0.8.5 can call `gemini-embedding-001` was not executed. **LIKELY** the SDK needs a bump or a move to `google-genai` when embeddings are repaired. Do not upgrade during the chat-only fix.

Imports that are easy to miss on a minimal install: `motor` (observability; log shows it initialized, so it is installed in production), `structlog` (optional), `sentry_sdk` (optional). Not declared in `requirements-minimal.txt`.

No CUDA/PyTorch requirement on the live path. `requirements-enhanced.txt` would be a problem on Render’s free tier if someone appended it. It is not currently installed by `build.sh`.

### Frontend

`frontend/package.json` is a Vite 5 / React 18 / Clerk 5 app. No `package-lock.json` was found, while CI asks for `npm ci` and then falls back to `npm install`. **CONFIRMED** missing lockfile. Builds are not reproducible. This did not cause the chat 404.

`date-fns` 3.x and `react-day-picker` 8.x are an older pairing. Not implicated in this incident.

Root `package.json` has no installable dependencies. It only has scripts that point at the missing `requirements.txt`.

### CI

`.github/workflows/ci.yml` installs `backend/requirements.txt` and will fail on a clean checkout. **CONFIRMED** from the workflow file. Tests were not run, because installing dependencies would modify the environment.

---

## 7. Environment Configuration Audit

Secret values are not recorded. “Present in production” means the running process behaved as if the variable was set. The repo contains no committed `.env` (`.env*` is gitignored, including `.env.example`).

| Variable | Used where | Required for live chat? | Default | Risk |
| --- | --- | --- | --- | --- |
| `GROQ_API_KEY` | `groq_client.py`, router v3, compound research | Yes | none | Present in this deploy (client constructed). Key cannot make retired model ids work. |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | embeddings | Not for a text reply; yes for memory | none | Required at startup check. Embedding model id is dead even if the key is valid. |
| `PINECONE_API_KEY` | Pinecone clients | Not for a text reply | none | Startup check. Index compatibility UNKNOWN. |
| `PINECONE_INDEX_NAME` | Pinecone | No | `my-chatbot-memory` | If unset, code assumes that index and 384 dimensions. |
| `PINECONE_ENV` | README only | No | — | Current Pinecone client does not use this. Stale docs. |
| `MONGODB_URI` or `MONGO_URI` | `database/db.py` | Yes for history | `mongodb://localhost:27017/chatbot_db` | Production connected. Local default would be wrong if unset. |
| `MONGO_DB` | observability Motor | No | `chatbot_db` | Must match the DB the sync client uses or llm-call logs go to a different database. **POSSIBLE** split. |
| `PORT` | process bind | Yes on Render | 8000 in local script | Log shows 8000. Fine. |
| `ENVIRONMENT` | startup strictness, CORS | No | `development` | Render blueprint sets `production`, which **skips** the hard fail on missing keys. |
| `DEBUG` | logging | No | false | — |
| `FRONTEND_URL` | CORS extra origin | No if origin is hardcoded | none | Blueprint still says `https://your-frontend-domain.vercel.app`. Live allow-list is hardcoded in `chatbot.py` and already includes `kuro-tau.vercel.app`. |
| `FRONTEND_URL_PATTERN` | CORS suffix | No | `.vercel.app` | Broad suffix is a footgun if combined with the pattern check. |
| `VITE_API_URL` / `VITE_API_BASE_URL` | `frontend/src/lib/api.ts` | Yes for the browser | `http://localhost:8000` | Production frontend reached the Render API, so one of these is set on Vercel. **CONFIRMED** by the log origin. |
| `VITE_CLERK_PUBLISHABLE_KEY` | `frontend/src/main.tsx` | Yes for login | none | Login worked far enough to send a user id. |
| `CLERK_SECRET_KEY` | `test_api_keys.py` only | No | none | Backend never verifies Clerk tokens. |
| `OPENROUTER_API_KEY` | OpenRouter client, old orchestrator | No on live path | none | Unused by the failing path. |
| `ADMIN_API_KEY` | `admin/auth.py` | No | none | Admin routes fail closed if unset. |
| `SENTRY_DSN` | optional | No | unset | Not in the log. |
| `DISABLE_MEMORY_INIT` | tests; switches `POST /chat` to v2 | No | unset | If set, live path changes to v2, which still calls the same dead Groq models. |
| `DISABLE_EMBEDDINGS` | `start.sh`, disabled embedding router | No | unset unless start.sh | Render log start command is raw gunicorn, not `start.sh`, so this export did not run. |
| `CIRCUIT_BREAK_THRESHOLD` | `reliability/circuit_breaker.py` | No | 5 | Log reached failure 4/5. Next turns will open the breaker and fail faster, still with a fake 200. |
| `CIRCUIT_BREAK_RESET_SECONDS` | same | No | 60 | Opens then probes again. No healthy model exists to recover. |
| `LTM_SIMILARITY_THRESHOLD` | long-term memory | No on v3 | 0.75 | v2 only. |
| `MAX_CONTEXT_TOKENS` | context builder | No on v3 | 28000 | v2 only. |
| `ROUTER_CONFIDENCE_THRESHOLD` | router v3 | No on live v3 manager | 0.6 | — |
| `OBS_DISABLED` | middleware | No | unset | Middleware is on. Mis-labels non-LLM calls. |
| `LOG_RAW_CONTENT` | middleware | No | false | — |

Hardcoded production origins in `chatbot.py` include `https://kuro-tau.vercel.app` with and without a trailing slash, duplicated, plus `http://kuro-tau.vercel.app/` (http, with slash only). The browser origin matched exactly. CORS is noisy, not broken, for this frontend.

`render.yaml` `FRONTEND_URL` is still a placeholder. It does not match the live frontend. The live allow-list does not depend on it for `kuro-tau`. **CONFIRMED** placeholder. **P3** unless a new domain is added only via that variable and the code path that reads it is wrong. Not the outage.

---

## 8. Backend Audit

### What works

- Process boot, signal handlers, `/ping`, CORS preflight, Mongo connect, session list, transcript read, user name, intro flag, chat insert. All **CONFIRMED** by the log.
- `POST /chat` schema matches the frontend body (`user_id`, `message`, `session_id`, `search_mode`, `skill`).

### What is broken

1. **Provider 404s are converted into HTTP 200.** `llm/router.py` returns `"I ran into a temporary issue while generating that response. Please try again."` and does not raise. `chat_endpoint` only uses `hardcoded_responses.generic_error` if `handle_chat` throws. It did not throw. The canned string is saved as the assistant reply. **CONFIRMED.**
2. **Every live model id is retired.** See section 5.
3. **One user turn spends three or four Groq calls** (intent, memory decision, answer, background extract) before any of them can succeed. After model ids are fixed, this will still multiply latency and rate-limit usage. The logged answer latency was 4029 ms of pure failure.
4. **`GroqClient.generate_content` re-routes even when `model_id` is passed.** The override happens after `route_model`, so logs lie about which model was chosen, and circuit-breaker keys follow the fallback chain rather than the caller’s model alone.
5. **Fallbacks cannot leave Groq.** Registry fallbacks are other dead Groq ids, or an OpenRouter id that `choose_fallback` drops.
6. **`search_mode` and `skill` are ignored** by the live manager. The frontend can request web search and a skill; nothing happens.
7. **Duplicate `GET /healthz`.** Defined twice in `chatbot.py` (around the early health routes and again later). FastAPI will keep one. Harmless but sloppy.
8. **Startup does not fail in production when keys are missing** (`ENVIRONMENT=production` skips the raise). A bad deploy stays “healthy”.
9. **Auth is absent.** Routes trust `user_id` from the client. The Clerk bearer token is not checked. Any caller who can hit the API can read or write any user’s sessions if they know or guess the id. **CONFIRMED** by absence of verification in `chatbot.py`. This is not why this user’s chat text failed.
10. **Sync Mongo and Pinecone work runs inside `async def` handlers** (`get_user_sessions`, `get_session_chat`, and the v3 retriever). `generate_content` is correctly pushed to a thread. DB calls are not. Fine at one worker and low traffic. It will stall the event loop under load.
11. **Background memory task is fire-and-forget.** Failures are logged inside the LLM client and then swallowed by the updater’s JSON parser. The HTTP handler does not know extraction failed.
12. **`@app.on_event("startup")`** is the deprecated FastAPI hook. It ran (`FastAPI startup complete`). Not the outage. It will warn or break on a future FastAPI that removes it.
13. **Broad `except:` in `LLMRouter.GenericModel.__init__`** hides a missing `GROQ_API_KEY` and later returns an empty string, which v3 turns into another canned line. In this log the key was present, so this branch did not run.

### Endpoint trace

| Endpoint | Result in this log | Contract |
| --- | --- | --- |
| `OPTIONS` + `GET /ping` | 200 | Frontend health probe. Middleware logs it as an LLM call. |
| `GET /sessions/{user_id}` | 200, 1 session | Matches frontend. |
| `GET /user/{id}/has-name`, `/name`, `/intro-shown` | 200 | Matches `api.ts`. |
| `GET /chat/{session_id}` | 200 | Returns history. Frontend maps it. |
| `POST /chat` | 200 with a non-answer | Body shape is fine. Semantic result is a failure. |
| `/store-memory`, `/retrieve-memory` | Not in this log | Still bound to ultra-lightweight memory and dead embeddings. |
| `/inline-query` | Not in this log | Separate path; if it uses GroqClient or v2, it will 404 the same way. **LIKELY.** |

---

## 9. Frontend Audit

The production UI is the Clerk-backed chat at `/chat` and `/chat/:sessionId` (`frontend/src/pages/Chat.tsx`, `use-chat-panel.ts`). Older pages (`Landing.tsx` vs `LandingNew.tsx`, mock data in `frontend/src/data/mockData.ts`) are leftovers. Mock helpers still say `TODO: Replace with fetch` and are not the live client.

Live client: `frontend/src/lib/api.ts`.

- Base URL is `VITE_API_URL` or `VITE_API_BASE_URL`, else `http://localhost:8000`. Production is not using the default, because the browser hit Render.
- Axios sends `withCredentials: true` and `Authorization: Bearer <clerk jwt>` when the hook is used.
- `POST /chat` payload matches `ChatInput`.
- Response fields `reply`, `model`, `route_rule`, `latency_ms`, `suggest_search` match `ChatResponse`.
- There is no streaming. The UI waits for the full JSON body. Nothing in the live backend streams tokens. That part is consistent.
- After a 200, the hook appends the reply, then **reloads history from Mongo** and replaces local state. The persisted canned error becomes the visible message. **CONFIRMED** in `use-chat-panel.ts`.
- Error detection only looks for phrases like “Rate Limit”, “Quota”, “Server Error”. The v3 string “temporary issue while generating” is classified as a normal assistant message. **CONFIRMED.**
- `model: "v3_model"` will render if the bubble prints `message.model`. It is not a provider model name. Cosmetic.

No frontend build was run. Static review did not show an import or route bug that would explain this log. The frontend did its job: it delivered the turn and displayed what the API stored.

---

## 10. Memory Audit

Two memory designs are both still in the tree. They do not share one lifecycle.

### Live v3 lifecycle

```
user message
  → LLM intent JSON          (failed)
  → LLM memory decision      (failed, rule fallback, usually use_memory=false)
  → Pinecone query           (skipped this turn)
  → prompt with history from Mongo (last 20 messages only)
  → LLM answer               (failed)
  → background extract/score/merge
       → LLM JSON            (failed, stored nothing)
       → Mongo memories_v3 + Pinecone upsert
```

Short-term memory, as actually implemented, is the last 20 Mongo messages loaded in `chat_endpoint`. That part does not need embeddings and worked.

There is no progressive summarization on the v3 path. v2 explicitly removed it and replaced it with “raw history now, one summary later”. v3 does not call that summarizer either.

Long-term memory on v3 is `MemoryUpdater` → `memories_v3` → Pinecone. Extraction did not succeed in the log, so this turn wrote no memory. **CONFIRMED** that the extraction call 404’d. **LIKELY** that `memories_v3` was unchanged.

### Retrieval bugs that will show up after chat works

- `MemoryRetriever.retrieve` drops any hit whose metadata `importance` is not **greater than 3**. The updater scores importance from 1 to 10, so low-scoring facts never return. Older memories stored on a 0–1 scale would all be dropped. **CONFIRMED** filter. **UNKNOWN** which scale is already in Pinecone.
- Reranking calls `llama-3.3-70b-versatile` and, on any failure, returns the unreranked list. After a model fix this is acceptable. Today it cannot rerank.
- `reinforce_memories` increments importance and re-embeds. It did not run this turn because retrieval was skipped.
- User isolation is a Pinecone metadata filter on `user_id`. That is the right idea. It is only as good as the id the client sends. There is no server-side binding to Clerk.
- Session ids are not part of the vector filter. v3 memories are per user, not per session. That is cross-session by design. It is not leakage between users unless ids collide or a client spoofs `user_id`.
- Duplicate detection uses vector score ≥ 0.85. With the current embedding function that score is not meaningful (next section).
- Zero-vector fallback: if embedding throws, `db/pinecone.py` returns 384 zeros and still upserts. Failures become stored junk instead of a hard error. **CONFIRMED** in code. Not proven against the live index in this log.
- Unbounded growth: nothing in v3 deletes or consolidates except an explicit `/user/{id}/cleanup` route that belongs to the older manager. v3 insert path does not cap count.

### v2 / ultra-lightweight lifecycle (not this request)

v2 keeps raw session messages and writes one Pinecone summary at session close or at 50 messages, via `long_term_memory.py`, same `text-embedding-004`. Skills and model lock live here. `POST /chat` does not call it.

`/store-memory` and `/retrieve-memory` still call the ultra-lightweight manager. A client using those routes is on a third schema.

---

## 11. RAG Audit

There is no document-ingestion product path on `POST /chat`. RAG here means “embed a memory string and query Pinecone”.

| Stage | Live v3 behavior | Problem |
| --- | --- | --- |
| What is indexed | Memory strings extracted from a turn, not uploaded files | Extraction LLM is dead, so indexing does not happen |
| Embedding model | `models/text-embedding-004` | Shut down 14 Jan 2026. **CONFIRMED** by Google changelog |
| Dimension | Code comments say Gemini returns 768 and the index expects 384. Implementation keeps every second value (`vec[::2][:384]`) | This is not a real reduction. It destroys the vector. Queries and documents are “compatible” with each other only because both are damaged the same way. Quality is poor even when the model existed. |
| If embed throws | 384-dimensional zero vector | Pollutes the index |
| Store | Pinecone upsert with metadata `user_id`, `type`, `importance`, `content` | No namespace strategy. Default index name if env is unset |
| Retrieve | Metadata filter `user_id` and `type $in` | Then an importance > 3 cutoff the retriever adds itself |
| Top-k | Controller asks up to 10, retriever fetches up to 20, rerank keeps 5 | Reasonable shape, unreachable while embed and LLM are dead |
| Rerank | Another LLM call | Same Groq outage |
| Prompt injection | `PromptBuilder` inserts retrieved texts | Skipped when retrieval is skipped |
| Citations | None | — |
| Existing vectors | Written with `text-embedding-004` truncated to 384 | **Not compatible** with `gemini-embedding-001` (3072 default, or a chosen `output_dimensionality`) or with `gemini-embedding-2`. A model swap without a re-index will query a different space, or fail the dimension check. **CONFIRMED** incompatibility of embedding spaces from Google’s docs. **UNKNOWN** whether the live index is actually 384-d. |

`retrieval/pipeline.py` is a separate ingest/rank path used by the ultra-lightweight manager. It is not the v3 retriever. Fixing one does not fix the other.

---

## 12. Intent / Router Audit

Live intent handling is not `routing/intent_classifier.py` and not `model_router_v3.py`.

`ChatManagerV3._analyze_intent` asks `llama-3.1-8b-instant` for JSON. On failure, `_safe_json_parse` produces a weak default (the exact default is in the rest of that file; the LLM error string is not valid JSON). `MemoryController` then cannot trust `needs_memory` and its own LLM call also fails, so it uses the rule fallback. For a normal chat that fallback is `use_memory: false`. **LIKELY** for the logged casual turn, and consistent with no retrieval log line.

Style routing after that is keyword-based in `_normalize_style_intent` (`code`, `reasoning`, `summarization`, else `conversation`). It does not use the skill field from the client. A casual message stays on `conversation` → `llama-3.3-70b-versatile`. **CONFIRMED** against the log’s final model error.

`routing/model_router.py` still classifies the same prompt as `casual_chat` → `llama-3.3-70b-versatile` because `GroqClient` calls it unconditionally. That decision is discarded when `model_id` is passed. It does determine log lines and can affect the attempt only if `model_id` is omitted.

Failure behavior:

- Low confidence: v3 manager has no confidence score.
- No model: canned string, HTTP 200.
- Fallback: dead Groq ids only.
- Loop: the fallback walker stops when `choose_fallback` returns `None`. No infinite loop. **CONFIRMED.**
- Circuit breaker: after 5 consecutive failures the model is skipped for 60 seconds, then probed again. Every probe will 404. The breaker does not select a healthy provider.

`model_router_v3.py` is a real classifier (cache, LLM JSON, optional compound research) but `ChatManagerV3` never calls `get_best_model`. The name collision is misleading. The class `ChatManagerV3` and the module `model_router_v3` are different systems.

---

## 13. Skills / Tools Audit

`backend/skills/skills.json` defines prompt modes, not executable tools: `creator_info`, `casual_chat`, `farewell_chat`, `fact_check`, `clarifier`, `debugging`, `math_solver`, `summarizing`, and others in the rest of the file. Each has trigger phrases and a system-prompt overlay. There is no input schema, no side effect, and no external API per skill.

| Skill module | Reachable from `POST /chat`? |
| --- | --- |
| `skills/skill_manager.py` | No. Used by `chat_manager_v2` and `llm_orchestrator`. |
| `skills/skill_manager_lightweight.py` | No duplicate-style alternate. |
| `skills/skill_manager_old.py` | No. |

The frontend sends `skill: 'auto' | ...`. The API stores it on the pydantic model and drops it. **CONFIRMED.**

`routing/compound_research.py` is the only tool-like call (Groq compound web search). It is invoked from router v3 / chat manager v2, not from `ChatManagerV3`. `groq/compound-mini` has no replacement id and was decommissioned today. Research cannot be restored by renaming a model. It needs a different search design.

No MCP client is wired into the backend runtime. Cursor MCP config in the workspace is an editor setting, not a Kuro feature.

---

## 14. Database Audit

### MongoDB

Connection in the log: `database.db` connected on PID 44 in about 1.5 seconds. **CONFIRMED.**

Collections touched by code:

| Collection | Writer | Reader | This request |
| --- | --- | --- | --- |
| Sessions / chats via `chat_database.py` | `save_chat_to_db` | `get_sessions_by_user`, `get_chat_by_session` | Read and write succeeded. The write stored the error sentence. |
| `memories_v3` | `db/mongo.py` | semantic lookup | Not successfully written this turn. |
| `llm_calls` | observability Motor | metrics | Motor initialized. Whether this request was upserted was not visible in the snippet. |
| Older memory collections | ultra-lightweight / v2 | legacy routes | Not this request. |

Indexes: `memory.chat_database` logged `Database indexes verified` during the request. **CONFIRMED** that the check ran. The index definitions were not compared to query patterns in this pass.

`datetime.utcnow()` is used on memory documents. That is naive UTC. It still sorts. Not a functional break.

No migration was inspected. No data was modified.

### Pinecone

Code assumes one index, default name `my-chatbot-memory`, vectors of length 384, cosine-style similarity (metric is whatever the index was created with; the code does not set it).

Metadata written by v3: `id`, `content`, `user_id`, `type`, `importance`.

Not verified against the live index: dimension, metric, pod vs serverless, and whether old 768-d vectors exist under another index. **UNKNOWN.** If the index is not 384-d, upserts fail inside a `print`/`except` and look like success to the caller.

Do not delete or re-index during the first chat repair.

---

## 15. Logging and Error Handling

| Observation | Assessment |
| --- | --- |
| Groq 404 is logged with the URL and then again as `llm.router` model error | Provider failure is distinguishable in server logs. **CONFIRMED.** |
| Stack traces | `chat_endpoint` uses `exc_info=True` only when it catches. The Groq failure is caught earlier and logged as `%s` of the exception, not a traceback. Enough to diagnose this incident. |
| Client response | HTTP 200 and a friendly sentence. The frontend cannot tell provider failure from a real answer, except by reading the sentence. |
| `model` / `route_rule` | Hardcoded `v3_model` / `v3_rule`. The failing model id is not returned. |
| Request ids | Middleware creates them and logs `llm_request_complete` with `request_id`. They are not attached to the Groq error lines, so the 404s cannot be joined to the access line without timestamps. |
| `llm_request_complete` on `GET /ping` and `GET /sessions` | The middleware treats every non-health request as an LLM call. `/ping` is not in `HEALTH_PATHS` (`/healthz`, `/live`, `/ready`, `/metrics` only). Misleading, not fatal. |
| CORS logging | Every request prints the full origin list at INFO. High volume, low value. |
| Swallowed errors | `MemoryController` bare `except: pass`. Updater JSON `except: return empty`. Pinecone `print` on failure. `GenericModel.__init__` bare `except: pass`. These hide the next failure after models are fixed. |
| Circuit breaker warnings | Accurate. They count dead models toward open state. They are a symptom. |

Silent failure the user actually hits: **the assistant reply is the error string, stored permanently in the transcript.**

---

## 16. Test Audit

Tests were not executed. Installing `requirements.txt` is impossible in this tree, and installing the minimal file would change the environment.

| Area | Files | Gap |
| --- | --- | --- |
| Live `ChatManagerV3` / `llm/router.py` | No dedicated test found | The path that serves production is untested. |
| Model ids | `tests/test_model_normalization.py` | Asserts legacy OpenRouter normalizations such as `deepseek-r1` → `deepseek/r1`. Does not assert that Groq ids still exist. Will stay green after a provider shutdown. |
| Router v2 | `test_model_router_v2.py`, `test_routing_and_resilience.py` | Cover the unused router. |
| v2 chat | `test_orchestrator_integration.py`, `test_improved_memory.py` | Import `chat_manager_v2`. |
| Embeddings | `test_memory_system.py`, `verify_ai_setup.py` | Call `text-embedding-004`. Will fail against the live Gemini API. They are outdated, not protective. |
| Startup | `test_startup.py` | Imports the app. Would pass while chat is semantically broken, because import does not call Groq. |
| Middleware | `test_instrumentation_middleware.py` | Mocks chat. Does not catch the 200-on-404 behavior. |
| Prompt policy | `test_prompt_policy_regressions.py`, `test_research_search_advisory.py` | Useful for v2 safety copy. Not the outage. |

CI cannot install dependencies until `requirements.txt` is restored. **CONFIRMED.**

---

## 17. Dead Code and Technical Debt

Do not delete these in the first repair. They document previous behavior and some are still imported by tests.

| Item | Why it is debt |
| --- | --- |
| `routing/model_router.py`, `_v2.py`, `_v3.py`, `_lightweight.py`, `_minimal.py` | Four selectors. Live chat uses none of them for the final model choice, but v1 still runs inside GroqClient. |
| `routing/session_tracker_old.py`, `skills/skill_manager_old.py`, `skills/skill_manager_lightweight.py` | Previous copies. |
| `memory/chat_manager_v2.py` vs `chat_manager_v3.py` vs `ultra_lightweight_memory.py` vs `long_term_memory.py` | Three memory designs. Comments in `chat_endpoint` describe v2 while the code calls v3. |
| `orchestrator.py` and `orchestration/llm_orchestrator.py` | Second orchestration stack on OpenRouter. |
| `frontend/src/data/mockData.ts` | Unused fetch TODOs. |
| Duplicate page pairs (`Landing` / `LandingNew`, `SignIn` / `SignInNew`, `NotFound` / `NotFoundNew`) | Unclear which routes are canonical. `App.tsx` is the source of truth for production routes. |
| `backend/data/circuit_breaker.json` | File-based breaker state for the other circuit-breaker module. The live breaker is in-memory in `reliability/circuit_breaker.py`. |
| README and `render.yaml` | Describe LLaMA 3 on Groq, Gemini embeddings, and a placeholder frontend URL. |
| `.github/copilot-instructions.md` | Still names the removed Groq models and paths like `backend/orchestration/groq_client.py` that are not the live client. |
| `get_fallback_chain` in `model_config.py` | Has a `return` and then more statements that never run. |
| Hardcoded `v3_model` / `v3_rule` | Hides the real model from the UI and from logs at the access line. |

---

## 18. Log Analysis

| Log | Component | Root cause | Class |
| --- | --- | --- | --- |
| Gunicorn / Uvicorn boot, “Application startup complete” | Process | None. Healthy. | — |
| `observability_motor_initialized` | Motor | None. Mongo URI for observability worked. | — |
| CORS allow + `OPTIONS` 200 | `chatbot.py` middleware | None. Origin is allow-listed. | — |
| `llm_request_complete` on `GET /ping` | instrumentation middleware | `/ping` is not classified as health. Mislabel. | Code bug, P3 |
| Mongo connect + “Retrieved 1 sessions” | `database.db`, chat database | None. | — |
| `GET /user/...` 200 | user routes | None. | — |
| `Rule match: intent='casual_chat' -> llama-3.3-70b-versatile` | `routing.model_router` via `GroqClient._select_model` | Router still runs, then `model_id` overrides it. Not the model that 404’d on the first errors. | Code bug, P2, not the outage |
| Circuit breaker failure 1–4 for the three Groq ids | `reliability.circuit_breaker` | Each fallback attempt records a failure because Groq returns 404. | Symptom |
| `Groq API request failed: 404 ... /chat/completions` | `utils.groq_client` | Model id retired. Endpoint URL is still valid. | Model/provider |
| `Error generating from model llama-3.1-8b-instant` (twice) | `llm.router` | Intent call, then memory-decision call. | Model/provider, then swallowed |
| `Error generating from model llama-3.3-70b-versatile` before “Chat response” | `llm.router` | Answer call. | Model/provider |
| `Chat response ... model=v3_model` and `POST /chat` 200 | `chatbot.py` | Exception was swallowed. Status does not mean the model answered. | Code bug |
| `Chat saved` | `chat_database` | Error string persisted. | Consequence |
| Second `llama-3.3-70b-versatile` 404 after the 200 | `MemoryUpdater` | Background extraction. | Model/provider, silent |
| Following `GET /chat/...` 200 | history | Frontend reloaded the stored error string. | Consequence |

Not a database outage. Not a CORS outage. Not an auth outage. Not a frontend contract mismatch for this turn.

---

## 19. Cascading Failure Analysis

```
Groq shut down llama-3.1-8b-instant, llama-3.3-70b-versatile,
and (earlier) deepseek-r1-distill-llama-70b and mixtral-8x7b-32768
        ↓
Live router still sends those ids to /openai/v1/chat/completions
        ↓
Groq responds 404
        ↓
GroqClient walks registry fallbacks; every hop is also retired
        ↓
OpenRouter id in the registry is ignored because it is not a registered model
        ↓
llm/router.py catches the error and returns a fixed sentence
        ↓
ChatManagerV3 treats that sentence as the assistant reply
        ↓
chat_endpoint returns HTTP 200 and writes the sentence to Mongo
        ↓
Frontend history reload displays it as a normal Kuro message
        ↓
Memory extraction task 404s as well and stores nothing
        ↓
Circuit breaker counts toward open; later requests fail faster
and still return 200
```

Separate cascade, not triggered by this particular turn, but next:

```
text-embedding-004 shut down (Jan 2026)
        ↓
Pinecone embed throws
        ↓
code substitutes a 384-d zero vector (or the query returns [])
        ↓
retrieval is empty or nonsense
        ↓
even after chat models work, long-term memory stays wrong
until the embedding model and the index are migrated together
```

Research cascade, if someone re-enables v2 or calls compound directly:

```
groq/compound-mini decommissioned 21 Sep 2026 with no replacement id
        ↓
search_mode cannot be implemented by renaming the model
```

---

## 20. Root-Cause Matrix

| ID | Component | Problem | Root cause | Evidence | Severity | Depends on | Recommended fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL-001 | Groq chat | All live completions 404 | Retired model ids | Log + Groq deprecations page | P0 | None | Point the live path at current Groq ids (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and a current summarizer). Confirm with `GET /openai/v1/models` before editing. |
| MODEL-002 | Registry + Groq map | Fallbacks are also retired | `model_registry.yml` and `groq_client.groq_model_map` were not updated when Groq shut models down | Registry file; deprecation dates | P0 | MODEL-001 | Update fallbacks in the same change so one 404 does not walk three dead ids. |
| MODEL-003 | Router v3 / compound | Research model dies today | `groq/compound-mini` shutdown 21 Sep 2026, no replacement | Groq deprecations | P1 | A search design, not a rename | Leave research off until a replacement exists. Do not block basic chat on it. |
| MODEL-004 | Embeddings | Memory vectors cannot be created or queried correctly | `text-embedding-004` shut down; code also slices 768→384 | `db/pinecone.py`; Google changelog | P1 | Chat can work without this | Switch to `gemini-embedding-001` with an explicit dimension, then re-embed. Do not do this in the first chat patch. |
| MODEL-005 | `model_config.py` | Large map of removed OpenRouter and Groq ids | Stale catalog used by non-live routers and tests | File contents | P2 | MODEL-001 | Update after the live path, or stop calling this map from production. |
| API-001 | `llm/router.py` + `chat_endpoint` | User sees a fake successful answer | Exceptions become a string; HTTP status stays 200; string is stored | Log `POST /chat` 200 after the 404; router line 43 | P0 | MODEL-001 should land with this | Surface provider failure. Do not persist the canned sentence as a real answer. |
| API-002 | `ChatManagerV3` | `search_mode` and `skill` ignored | Live manager never reads them | `chatbot.py` model vs `handle_chat` signature | P2 | MODEL-003 for search | After chat works, either honor them or stop advertising them. |
| API-003 | `GroqClient` | Logs and routing disagree | `route_model` runs even when `model_id` is set | Log “casual_chat → 70b” followed by an 8b error | P2 | MODEL-001 | Skip re-routing when the caller passed a model. |
| API-004 | Auth | Any client can pass any `user_id` | Bearer token is not verified | No auth dependency on chat routes; frontend still sends a token | P1 | None, but not the text-generation outage | Verify Clerk JWT and derive `user_id` from it. |
| MEM-001 | Updater | No new long-term memories | Extraction model 404s; JSON parse returns empty | Post-200 404 in the log | P1 | MODEL-001 | Will start failing differently until MODEL-004 is fixed. Do not expect memories to work on the chat-only patch. |
| MEM-002 | Retriever | Relevant memories can be dropped | `importance > 3` filter | `retriever.py` | P2 | MEM-001 | Align the scale with stored metadata after inspecting real documents. |
| MEM-003 | Pinecone helper | Failed embeds can be stored as zeros | `except` returns `[0.0] * 384` | `db/pinecone.py` | P1 | MODEL-004 | Fail closed. Never upsert a zero vector. |
| RAG-001 | Embeddings | Stored vectors will not match a new model | Different embedding space; current vectors are subsampled 384-d | Google docs + slice code | P1 | MODEL-004 | Re-index. Keep the old index until the new one is populated. |
| DEP-001 | Build | Clean install and CI cannot run | `requirements.txt` is absent; scripts and CI require it | Repo search; `build.sh`; `ci.yml` | P1 | None | Restore a lock-style requirements file from the last known good deploy. Do not “upgrade everything” while doing it. |
| DEP-002 | Frontend | Non-reproducible UI build | No `package-lock.json` | Repo search | P3 | None | Regenerate a lockfile later. |
| OBS-001 | Middleware | Ping and session GETs look like LLM calls | Health skip list omits `/ping`; logger name is `llm_request_complete` | Log lines for `/ping` | P3 | None | Rename or filter. |
| OBS-002 | Chat response log | Access log hides the real model | Hardcoded `v3_model` | `chatbot.py` | P2 | API-001 | Log the provider model id and whether generation succeeded. |
| CFG-001 | `render.yaml` | Blueprint frontend URL is a placeholder | `https://your-frontend-domain.vercel.app` | `render.yaml` | P3 | None | Point at the real Vercel origin when the blueprint is next used. |
| SEC-001 | CORS | `http://` variant and duplicated origins; pattern can be broad | Allow-list construction | Log “Allowed origins” | P3 | None | Tighten after chat works. Current production origin is allowed. |
| TEST-001 | Tests | Production path has no test that would catch a 404-as-200 | No ChatManagerV3 test; CI cannot install | Test file list | P2 | DEP-001, API-001 | Add one test that a provider 404 does not become a stored assistant message. |

---

## 21. System Health Status

| Component | Status | Evidence |
| --- | --- | --- |
| Backend process | **Working** | Gunicorn booted, startup complete, Mongo connected. |
| HTTP API shell | **Partially working** | Health, sessions, history, profile: 200. Chat: 200 with a fake body. |
| Frontend | **Partially working** | It authenticates, loads history, posts chat, and renders the stored reply. It cannot tell this reply is a failure. |
| Chat pipeline | **Broken** | Generation does not return model text. |
| Model layer | **Broken** | All live Groq ids are past shutdown. URL and API key usage are otherwise coherent. |
| Memory (transcript) | **Working** | Mongo history read/write succeeded. |
| Memory (long-term) | **Broken** | Extraction call failed. Embedding model is shut down. Dimension hack would still make retrieval poor after a model rename. |
| RAG | **Broken** | Same embedding path. No separate document index was found on the live chat path. |
| Database (Mongo) | **Working** | Connect and session queries in the log. |
| Database (Pinecone) | **Unknown** | Not touched successfully in this log. Code will not match a current Gemini embedding without a re-index. |
| Skills | **Unused** | Not invoked by the live manager. Definitions themselves are prompt text, not broken tools. |
| Intent routing | **Partially working** | Keyword style routing runs. The LLM intent step 404s. The extra `model_router` classification is ignored. |
| Tests | **Not representative** | They target v2, old model maps, and a requirements file that is not in the tree. Not executed. |
| Deployment | **Partially working** | The current instance is up. The repo cannot reproduce that build. `start.sh` is not the command Render ran. |

---

## 22. Must-Fix Issues

These are the blockers for “Kuro answers a chat message”.

1. **MODEL-001 / MODEL-002.** Replace retired Groq ids on the live call chain: `backend/llm/router.py`, `backend/utils/groq_client.py` (default, map, and fallbacks), and `backend/config/model_registry.yml`. Verify the replacement ids with Groq’s current model list before writing them in. As of the deprecation page today, the documented successors are `openai/gpt-oss-20b` (for the old 8B) and `openai/gpt-oss-120b` (for the old 70B). `qwen/qwen3.8-27b` is the successor of the already-removed `qwen/qwen3.6-27b`, not an extra reason to pick a preview model.
2. **API-001.** A Groq failure must not be stored as the assistant message or returned as an ordinary success. The UI already reloads history; if the bad string is saved, the user will keep seeing it.
3. **DEP-001, before the next deploy.** Put back `backend/requirements.txt` matching what production already runs, so the model-id fix can ship. A clean Render build will fail without it.

Not required for the first successful reply:

- Embedding migration and re-index (MODEL-004, RAG-001).
- Compound research (MODEL-003).
- Clerk verification (API-004), which is a real security hole but not why this reply was empty.
- Collapsing v2/v3/routers.
- Skills.

---

## 23. Recommended Repair Order

### Phase 1 — Make one chat completion succeed

- Restore `requirements.txt` from the deployed environment or the last commit that had it. Do not upgrade the set.
- Confirm live Groq model ids (`GET /openai/v1/models` with the existing key).
- Change only the ids the live path sends: `LLMRouter`, `GroqClient` default and map, registry fallbacks used by `choose_fallback`.
- Keep the same Groq URL, timeout, and message shape.

Why first: nothing else can be judged while every completion 404s.  
Expected result: `POST /chat` returns model text, and the Groq log line is absent.

### Phase 2 — Stop lying about success

- If the provider fails, do not call `save_chat_to_db` with the canned sentence.
- Return a non-200 or a response flag the frontend already knows how to treat as an error.
- Log the actual model id instead of `v3_model`.
- Add one test around that behavior once dependencies install.

Why second: a green model call can still be followed by a later 429 or 404, and the current code will write that into the transcript.  
Depends on Phase 1 only for manual verification. The status-code fix can be written in the same change.  
Expected result: failures stay out of Mongo and show as errors in the UI.

### Phase 3 — Cut useless model calls on the hot path

- Do not call Groq for intent and memory-decision until those calls use a live small model and a strict JSON parse.
- Do not call `route_model` when `model_id` was provided.
- Leave `search_mode` disabled rather than pointing it at `groq/compound-mini`.

Why after Phase 1: these are multipliers, not the reason the first token is missing.  
Expected result: one user message costs one Groq completion for a casual chat.

### Phase 4 — Memory and RAG

- Replace `text-embedding-004` with `gemini-embedding-001` and set `output_dimensionality` explicitly.
- Stop zero-vector upserts.
- Create or resize the Pinecone index to that dimension. Re-embed `memories_v3`. Do not query old 384-d sliced vectors with the new model.
- Then re-enable extraction and retrieval.
- Revisit the importance > 3 filter against real documents.

Why after chat: transcript history already works, and a bad re-embed destroys the only copy of vectors.  
Expected result: a new fact can be written and retrieved for the same `user_id`.

### Phase 5 — Skills, research, auth, tests

- Decide whether `POST /chat` should keep using `ChatManagerV3` or move back to v2. Do not run both.
- If research stays, replace compound with a real search tool. There is no Groq model id to swap in.
- Verify Clerk tokens and ignore client-supplied `user_id`.
- Delete duplicate routers only after nothing imports them and tests cover the one remaining path.

---

## 24. Longer-Term Improvements

- One model registry. Delete the duplicate maps after the live path is the only caller.
- One memory pipeline. v2, v3, and ultra-lightweight should not all write vectors.
- Backend authorization.
- Structured provider errors (status, model id, request id) through to the UI.
- Stop logging every CORS allow-list at INFO.
- A lockfile for the frontend.
- Replace `on_event` with a lifespan handler when FastAPI is next bumped, not before.
- Do not turn on `requirements-enhanced.txt` / torch on the Render free tier.

---

## 25. Unknowns / Information Needed

1. The response body of the logged `POST /chat`. The server-side string is inferred from `llm/router.py`. A copy of the JSON `reply` would confirm the user saw that sentence and not a different fallback.
2. `GET https://api.groq.com/openai/v1/models` for this key. Required before choosing replacement ids, in case the account is enterprise and still allowed to call the old Llama ids (the 404s make that unlikely).
3. Whether `backend/requirements.txt` exists on the Render build or in git history but not in this working tree.
4. Pinecone index name, dimension, and metric actually configured in the dashboard.
5. A sample `memories_v3` document and one Pinecone metadata record, to see the real importance scale and vector length. Do not print user content into the repo.
6. Whether `GEMINI_API_KEY` can call `gemini-embedding-001` with the installed `google-generativeai` version.
7. Frontend console errors, if any. The supplied log does not show a browser failure.
8. Whether later turns opened the circuit breaker (`failure 5/5` and “OPENED”). The snippet stops at 4/5.

---

## Audit Conclusion

1. **What is preventing Kuro from working right now?**  
   The live chat path calls Groq model ids that Groq shut down (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, and their fallback `deepseek-r1-distill-llama-70b`). The HTTP API then hides that failure as a normal 200 and stores it.

2. **Top 5 root causes**  
   - MODEL-001: retired Groq chat models on the live path.  
   - MODEL-002: fallbacks are the same retired models, and the OpenRouter fallback is not actually selectable.  
   - API-001: provider exceptions are turned into assistant text and persisted.  
   - MODEL-004: `text-embedding-004` is shut down, so long-term memory cannot be repaired by the chat fix alone.  
   - DEP-001: `requirements.txt` is missing, so the fix cannot be rebuilt cleanly from this tree.

3. **Which model/provider integrations are broken or obsolete?**  
   Broken now: Groq `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `deepseek-r1-distill-llama-70b`, `mixtral-8x7b-32768`, `gemma2-9b-it`, `qwen/qwen3-32b`, `groq/compound-mini`. Gemini `text-embedding-004`. The Groq **endpoint** and the MongoDB integration are not obsolete. OpenRouter is unused, not proven down.

4. **Is the current architecture salvageable?**  
   Yes. The frontend, session API, Mongo transcript store, CORS, and Groq client shape are fine. Replace model ids and error handling. Do not rewrite the app to get a reply back.

5. **Minimum work to get basic chat working**  
   Update the live Groq ids (router, client map, registry fallbacks), stop saving failed generations, and restore `requirements.txt` so that change can deploy. One casual message should then take a single successful completion and return that text.

6. **What should not be changed in the initial repair**  
   Mongo session schema, the frontend request shape, the CORS allow-list entry that already matches `https://kuro-tau.vercel.app`, Clerk on the frontend, Pinecone data, the embedding pipeline, and the unused v2/skill/orchestrator modules. Do not re-index. Do not upgrade FastAPI, Pinecone, or the Gemini SDK in the same change as the model-id swap.

7. **What should be redesigned later**  
   Collapse to one router and one memory writer. Replace sliced 384-d embeddings and re-index. Replace compound research with an actual search tool. Verify Clerk on the server. Make tests cover `ChatManagerV3` and provider failures.

8. **What is still needed before implementation**  
   A live Groq model list for this API key, the missing `requirements.txt` (from Render or git history), and confirmation of the Pinecone index dimension before any memory work. Chat repair can start from the deprecation page plus the model list. Memory repair should wait for the index facts in section 25.
