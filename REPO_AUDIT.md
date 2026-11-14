# Kuro AI repository audit (working-tree review)

Scope: static review of the current working tree, focused on backend API/security, persistence, memory/RAG, frontend API/rendering, build/test setup, and operational readiness. Findings below are tied to inspected code and distinguish confirmed code-level exposure from deployment/configuration questions. This is not a penetration test, provider-backed evaluation, or full runtime test.

## Executive summary

Kuro has useful production building blocks (FastAPI, Clerk in the frontend, MongoDB/Pinecone integrations, LLM abstraction, Prometheus/Sentry hooks, and tests), but the inspected implementation does not yet support a production-ready claim. Most urgent is tenant authorization: handlers accept user/session identifiers from request data and several session mutations/reads query only by session ID. The apparent authentication token on the frontend does not provide protection unless the backend validates it and derives identity; no such dependency is applied on the inspected API routes. Other high-risk issues include permissive substring CORS matching, unauthenticated memory/admin-adjacent operations, unbounded or weakly validated payloads, non-durable/non-integrated lexical RAG, and race-prone in-memory response state/background memory updates.

The worktree is heavily modified (129 reported modified paths, including an embedded submodule). Findings describe current files; do not treat this as a clean baseline or overwrite its changes. No edits were made during audit.

## Findings

### Critical / P0 — API does not enforce identity or ownership at route boundary

Evidence: `backend/chatbot.py:275-279, 316-324, 490-523, 546-601, 667-718, 720-762, 781-814, 861-901`; route parameters and bodies carry `user_id` / `session_id`. Session deletion/rename/history functions in `backend/memory/chat_database.py:242-255, 290-326` filter by `session_id` only; session title updates also key on session ID only (`:71-94`). The frontend does use Clerk (`frontend/src/lib/api.ts:47-53`) for requests through `useClerkApi`, but ordinary exported helpers call `apiRequest` directly (`:58-78, :89-105, :108-127`), and backend handlers do not show a Clerk verification dependency.

Impact: unless protected by an uninspected trusted gateway, callers may impersonate another `user_id`, read or alter sessions by guessing/obtaining a session ID, write/query memory for arbitrary IDs, and invoke memory cleanup. CORS is not an authorization control.

Guardrail: require verified Clerk JWT on every user-data endpoint; derive principal from verified `sub`, ignore caller-supplied identity, check session ownership in every query/update/delete, and apply the same rule to memory namespaces. Add negative integration tests for user A accessing user B's session and memories. Keep health endpoints public and explicitly document them.

### High / P1 — CORS preview-origin check is a substring trust rule

Evidence: `backend/chatbot.py:188-190, 196-244` defaults pattern to `.vercel.app` and allows if that substring occurs anywhere in the supplied origin. `frontend_urls` includes localhost entries even in production (`:164-181`); CORS allows credentials (`:225-228, :238-243`).

Impact: a lookalike origin containing `.vercel.app` may receive credentialed CORS access; unnecessary dev origins remain enabled in production. This becomes especially dangerous alongside missing authentication.

Guardrail: replace custom middleware with FastAPI `CORSMiddleware`; exact allowlist per environment, strictly parse scheme/host/port, allow only owned preview project hostname patterns, no substring matching; test hostile lookalikes and credential behavior.

### High / P1 — Request limits and cost controls are absent at visible schema boundary

Evidence: `ChatInput` and `QueryInput` declare plain strings and unrestricted `top_k` (`backend/chatbot.py:304-324`); `InlineQueryInput` has unbounded selected text/context/parent/question (`:844-855`); `/chat` allows unlimited client turns and may fan out to intent, generation, and memory-update model calls (`backend/memory/chat_manager_v3.py:33-86, 112-120`). No endpoint-level rate limiter or request-size enforcement is visible in `chatbot.py`.

Impact: oversized requests, prompt/token abuse, expensive repeated model work, memory pollution, latency spikes, and provider quota exhaustion.

Guardrail: Pydantic `min_length`/`max_length`, bounded `top_k`, JSON body byte limit, per-user/IP concurrency and request/token budgets, provider timeout/deadline, bounded retries, idempotency keys, and explicit max output tokens. Rate-limit auth-sensitive endpoints; protect cost-expensive search/retrieval separately.

### High / P1 — RAG implementation appears disconnected and lexical retrieval is ephemeral

Evidence: `backend/retrieval/__init__.py:50-69` creates a fresh `InMemoryKeywordIndex`; `ingest_document` only adds to that in-memory instance (`:84-90`), so it is lost on restart and per-worker in a multi-worker deployment. The inspected active chat path is `chatbot.py:585-601` to `ChatManagerV3`; `backend/memory/chat_manager_v3.py:51-79` uses `MemoryRetriever` rather than `RAGPipeline`. No evidence found in that path that `get_rag_pipeline()` is invoked. Current retrieved objects appear to be user memories, not a versioned corpus/document RAG pipeline.

Impact: advertised hybrid multi-pass RAG may not be active in chat; lexical recall disappears across restarts/workers; corpus grounding, citations and retrieval quality cannot be asserted from the current path.

Guardrail / quality plan: first define intended knowledge sources (user memory vs uploaded/curated documents) and route them through explicit separate retrieval services. Make ingestion durable and versioned; maintain source IDs, access-control metadata, chunk offsets, document version/hash, timestamps and provenance. Use hybrid dense + lexical retrieval with reciprocal-rank fusion, query rewriting only where measured, cross-encoder reranking, dedupe/diversity, relevance thresholds and abstention when evidence is weak. Pass evidence as untrusted quoted data, not instructions; attach citations to claims. Build a fixed gold set and measure Recall@k, MRR/nDCG, answer groundedness/citation accuracy, abstention quality, latency and cost before tuning.

### High / P1 — Chat persistence failure is silently returned as success

Evidence: `backend/chatbot.py:620-640` logs a failed `save_chat_to_db` but still returns HTTP success and the assistant reply. Session creation also falls back to the shared literal `default` if creation fails (`:558-567`).

Impact: user sees a successful answer that is absent from history; writes may be associated with a shared default session, undermining isolation and continuity.

Guardrail: never use a global/default session for authenticated traffic. Return explicit degraded/persistence status or fail safely; use transactional/idempotent turn records with request IDs, and reconcile accepted responses to durable storage. Alert on persistence failure rates.

### High / P1 — Backend startup can report success while required services are unavailable

Evidence: missing env check prints missing names, then skips raising whenever `ENVIRONMENT == production` (`backend/chatbot.py:26-40`); constructors initialize the chat manager at module import (`:50-67`); `/ready` always reports ready (`:356-359`).

Impact: deployment can become live despite missing secrets/dependencies; readiness does not protect traffic from an unusable instance. Conversely, production missing-key behavior is fail-open at this check.

Guardrail: validate required configuration with typed settings and fail startup on invalid production config; implement readiness checks for actually required dependencies with short timeouts and sanitized output; distinguish liveness from readiness; avoid network calls at module import and use lifespan startup/shutdown.

### High / P1 — Sensitive debug/operational endpoints lack an obvious access policy

Evidence: `/metrics` is directly exposed (`backend/chatbot.py:246-254`); `/api-status` sends a real provider request (`:380-420`); `/health` returns vector count and raw exception text (`:817-840`); user memory context and cleanup endpoints are directly mounted (`:781-814`).

Impact: resource usage, internal error details, and personal memory may be exposed or abused. Provider health probing can incur cost on every call.

Guardrail: protect operational/admin endpoints via network policy or strong service auth; expose only minimal health state publicly; redact errors; use cached dependency status rather than active paid generation probes; place metrics behind trusted scrape access.

### High / P1 — Memory extraction trusts model output and stores assistant-influenced content

Evidence: `backend/memory/updater.py:9-39, 41-70` asks an LLM to extract facts from both user and assistant messages, parses JSON with no schema/length/content validation, and persists any nonempty returned strings; importance parsing has fallback and no bounds (`:72-84`). Conflict resolution accepts raw generated content (`:86-96, 98-120`).

Impact: hallucinated assistant statements can become user facts; prompt injection can poison long-term memory; malformed/oversized values and importance values can degrade retrieval or expose data later.

Guardrail: extract only explicit user-provided assertions/preferences, require structured schema and strict field/size/range validation, retain source turn/provenance/confidence/expiry, ask confirmation for sensitive or consequential memories, permit inspect/edit/delete/export, and defend against prompt injection by treating conversation text as untrusted. Never persist an assistant claim as a user fact without user evidence.

### Medium / P2 — Memory update work is unbounded fire-and-forget and model call count multiplies

Evidence: `backend/memory/chat_manager_v3.py:112-120` starts one task per chat response with no queue/backpressure or shutdown drain. `backend/memory/updater.py:21-39` can score every extracted memory with a separate LLM call and then call conflict resolution (`:98-120`).

Impact: task loss on process termination, event-loop/resource overload under concurrency, cost/latency spikes, and excess model requests. Retries may duplicate writes absent idempotency.

Guardrail: durable task queue/outbox, bounded worker concurrency, dedupe keys, retry policy with dead-letter queue, shutdown drain, and metrics for queue depth/age/failures. Batch extraction/scoring or use deterministic rules where possible.

### Medium / P2 — Querying user history and session data has weak pagination/retention boundaries

Evidence: `get_sessions_by_user`, `get_chat_by_session`, and `get_all_chats_by_user` materialize entire result sets (`backend/memory/chat_database.py:192-240, 242-255, 274-288`); only chat generation trims context to last 20 exchanges (`backend/chatbot.py:587-595`).

Impact: memory/time cost and response sizes grow with lifetime usage; no explicit retention/export/delete policy is evident in these code paths.

Guardrail: cursor pagination with stable ordering, limits, projection, database query deadlines, TTL/retention policy where legally appropriate, user deletion workflow covering Mongo and vector stores, and backups/restore drills.

### Medium / P2 — Session ID generation collides for multiple sessions created in the same second

Evidence: `backend/memory/chat_database.py:102-105, 178-185` constructs IDs from user ID plus second-resolution timestamp; `create_new_session` inserts without a collision retry. The title collection has a unique session ID index only when index creation succeeds (`:36-55`).

Impact: simultaneous creation may collide, fail insert, or associate requests with wrong session, especially under concurrency.

Guardrail: use UUID/ULID IDs, unique constraints, atomic create/reuse semantics, and concurrent creation tests.

### Medium / P2 — Mongo index creation errors are swallowed, and writes perform non-atomic sequence allocation

Evidence: `_ensure_indexes` logs but does not propagate (`backend/memory/chat_database.py:36-57`); `_get_next_sequence_number` performs read then insert (`:59-69, 106-122`), so concurrent turns can share sequence numbers. `save_chat_to_db` then separately updates metadata (`:122-129`).

Impact: performance assumptions can silently fail; race conditions can reorder/equal-number turns and metadata counts may be stale.

Guardrail: ensure indexes in controlled startup/migration and alert/fail if critical indexes missing; use atomic counters or Mongo transactions/unique compound constraints; rely on timestamp plus stable ID for ordering.

### Medium / P2 — Memory reranking has fragile/no-score validation and silent fallback

Evidence: `backend/memory/retriever.py:34-84` interpolates raw query and retrieved text into a reranker prompt; accepts any finite or nonfinite float score and silently falls back to original order for every exception; returns model-provided rank without threshold. Initial retrieval drops all memories with importance <=3 (`:25-32`).

Impact: retrieved document prompt injection can affect reranker behavior; malformed rankings go unnoticed; low-importance but highly relevant memories are discarded; relevance errors are not observable.

Guardrail: replace LLM rank prompt with a dedicated reranker or strict typed scoring; escape/structure query and document fields; validate index uniqueness, score range and finiteness; keep scores and fallback telemetry; use retrieval relevance rather than a hard importance cutoff; evaluate thresholds on labeled examples.

### Medium / P2 — Frontend/runtime and test gates are not executable in current checkout environment

Evidence: root script `npm run lint` delegates to frontend; command failed with `eslint: not found`. Backend pytest invocation failed because the active Python lacks `pytest`; dependency is specified in `backend/requirements.txt:18`. Frontend has `type-check` but no test script (`frontend/package.json:7-18`); README claims tests that do not align exactly with package scripts (`README.md:373-387`).

Impact: current checkout has no verified lint/test pass; a change can reach deployment without executable CI gates. The failure is environmental, not proof tests fail.

Guardrail: use lockfile-based reproducible install (`npm ci`), pin Python lock/dependencies, run lint/typecheck/build and backend unit/integration/security tests in CI; add frontend component/E2E tests, coverage thresholds and protected-branch required checks. Confirm whether the untracked/ignored lockfiles are intentionally absent before modifying.

### Medium / P2 — Markdown code renderer trusts highlighted HTML output

Evidence: `frontend/src/components/MarkdownMessage.tsx:32-42, 80-84` runs highlight.js then inserts generated HTML with `dangerouslySetInnerHTML`.

Impact: code highlighting is an HTML injection sink; highlight.js normally escapes source text, but the safety depends on its contract and language/plugin behavior. This should not be an unverified trust boundary for model/user-controlled content.

Guardrail: prefer React-rendered token output or sanitize the generated HTML with a strict allowlist; add XSS regression tests with script tags, event attributes and unusual language identifiers. Keep raw model Markdown untrusted.

### Medium / P2 — App logs potentially identifying data and exposes backend topology to clients

Evidence: `backend/chatbot.py:203-207` logs every origin and full allowlist; chat logs user ID (`:615-618`); other endpoints log session/user IDs and memory IDs (e.g. `:503-504, :677-678`). Frontend logs API base URL (`frontend/src/lib/api.ts:12`).

Impact: personal identifiers can end up in application logs with unclear retention/access controls; verbose logging adds noise and may disclose deployment details.

Guardrail: use structured logs with opaque request IDs, pseudonymized identifiers, redaction, retention policy, and no message/token/API-key logging. Keep public build logs minimal.

### High / P1 — Admin LLM telemetry endpoint returns broad records with arbitrary limit

Evidence: `backend/admin/router.py:24-35` returns stored `llm_calls` documents without field projection and accepts a caller-selected limit; instrumentation includes user/session identifiers and error details (`backend/observability/instrumentation_middleware.py:102-116, 134-137`).

Impact: if admin auth is misconfigured or records are more widely visible than expected, internal identifiers and request metadata may be disclosed; a large limit can impose database/load costs.

Guardrail: project an explicit response allowlist, cap limit and paginate, redact/pseudonymize identifiers and error data, enforce admin role/access, define retention, and test unauthenticated and oversized requests.

### Medium / P2 — Startup allows missing required configuration in production

Evidence: `backend/chatbot.py:26-40` prints missing environment variable names but does not raise when `ENVIRONMENT == "production"`; separate provider/vector functions may degrade to empty outputs instead of failing readiness.

Impact: broken deployments can appear healthy while chat or retrieval is non-functional. This overlaps readiness finding above but is a separate configuration-validation defect.

Guardrail: typed settings validation must fail startup on missing required production secrets/configuration; optional services should be explicitly declared optional and reflected in readiness/degraded service status.

### High / P1 — Frontend does not fail fast when Clerk configuration is missing

Evidence: `frontend/src/main.tsx:8-16` logs a missing `VITE_CLERK_PUBLISHABLE_KEY` and continues mounting Clerk with placeholder `pk_test_missing`.

Impact: misconfigured production builds can ship with broken authentication rather than fail during build/deploy.

Guardrail: validate required build-time config during CI/build and render an explicit nonfunctional configuration state only in development; never silently use placeholder auth values in release builds.

### Medium / P2 — Profile/onboarding UI can claim persistence succeeded when it failed

Evidence: `frontend/src/experience/useKuroProfile.ts:88-115` updates local state and catches/swallows backend persistence failures.

Impact: user-facing state diverges from durable profile state, creating lost changes and confusing refresh behavior.

Guardrail: model pending/saved/failed states, only mark persisted after success, provide retry and offline messaging, and test backend failure/retry flows.

### Medium / P2 — Routed session loading has an unresolved missing-session path

Evidence: `frontend/src/hooks/use-chat-panel.ts:248-261` loads a routed session only if it is found in the session list; an empty list or unknown ID does not produce a visible not-found/error state.

Impact: deep links can leave the chat view blank or stuck when session listing fails or the requested session does not exist.

Guardrail: explicitly handle loading, list failure, unknown/deleted session, and unauthorized session states; test direct links and refresh.

### Medium / P2 — Frontend displays raw API error details directly in toast

Evidence: `frontend/src/hooks/use-chat-panel.ts:386-393` forwards caught error text; `frontend/src/lib/api.ts:25-43` derives messages from response detail/error fields.

Impact: internal provider/backend messages may be exposed to end users and the UI may show inconsistent or overly technical text.

Guardrail: map stable error codes to safe user-facing copy, keep diagnostic details in redacted telemetry, and preserve correlation IDs for support.

### Medium / P2 — Keep-warm behavior creates redundant requests on user activity

Evidence: `frontend/src/App.tsx:70-89` pings on focus/activity and maintains overlapping intervals.

Impact: unnecessary backend traffic and provider/hosting costs; activity-triggered pings can defeat intended idle behavior and complicate health telemetry.

Guardrail: remove the keep-warm client behavior in production; use hosting/provider health checks and a single bounded health signal only where operationally required.

### Medium / P2 — Sign-in/sign-up inputs lack programmatic accessible labels

Evidence: `frontend/src/experience/stages/Identity.tsx:226-255` uses placeholders without associated labels or `aria-label` for identity fields.

Impact: assistive technology may not expose field purpose reliably; placeholder-only forms are also less usable for users with memory/vision needs.

Guardrail: use explicit associated labels, accessible validation/status announcements, keyboard/focus tests, and automated accessibility checks.

### Low / P3 — Code copy fallback reports success without checking clipboard result

Evidence: `frontend/src/components/MarkdownMessage.tsx:46-58` calls `document.execCommand('copy')` but ignores its result and always switches state to “Copied.”

Impact: user receives false feedback when clipboard permission/API fallback fails.

Guardrail: check the fallback return value, show failure feedback, and announce status accessibly.

### Medium / P2 — Frontend test automation is absent or unverified

Evidence: `frontend/package.json:7-18` defines lint/type-check/build but no test script, and the frontend audit found no frontend test files. In this checkout, `node_modules` is absent so the frontend commands could not be executed.

Impact: UI/auth/session regressions and accessibility failures have no demonstrated automated regression gate.

Guardrail: add unit/component tests for API/auth and state flows, E2E tests for sign-in → chat → session persistence, accessibility checks, and run all in CI against reproducible installs.

## RAG quality and safety target design

1. Separate conversational memory from document knowledge. Store user memory under user-scoped namespaces; store source documents in separately permissioned indexes/collections.
2. Ingestion pipeline: parse/OCR → normalize → document metadata and ACL validation → semantic/structure-aware chunking with overlap → embeddings → durable vector + lexical index → versioned atomic publish. Preserve source, page/section, offsets, content hash and deletion lineage.
3. Retrieval: authenticate and enforce ACL before ranking; hybrid dense + BM25/lexical, rank fusion, query expansion/rewrite selectively, metadata filters, deduplication and diversity, then cross-encoder rerank. Use calibrated minimum relevance thresholds and return “not enough evidence” when below threshold.
4. Generation: include only selected evidence with stable citation IDs and provenance; clearly delimit untrusted context and instruct model not to follow document instructions; require citations for knowledge claims; post-validate citations against supplied chunks and provide abstention path.
5. Evaluation: curate representative queries, adversarial/prompt-injection cases, paraphrase/typo/multilingual cases, unanswerable questions, ACL boundary cases and stale/conflicting docs. Measure retrieval Recall@k/MRR/nDCG; answer correctness/faithfulness/citation precision; abstention calibration; latency, token and cost. Keep a frozen regression suite and compare every prompt/model/index change.
6. Production observability: trace request → auth → retrieval (candidate IDs/scores, sanitized) → model/provider → persistence; dashboards for p50/p95/p99, provider error/rate limit, retrieval empty/threshold rates, token cost, queue depth, persistence loss, auth denials and safety blocks. Avoid collecting raw user content by default.

## Guardrail layers

- Identity/authorization: Clerk JWT verification, principal-derived ownership, session/memory ACL enforcement, admin roles, automated cross-tenant tests.
- Abuse/cost: request schema bounds, rate and concurrency limits, user quotas, provider budget alerts, deadlines, idempotency and circuit breakers.
- Prompt security: untrusted user/document boundaries, injection tests, deny tools/actions unless explicitly authorized, output validation and no secrets in prompts/logs.
- Safety/privacy: policy classifier only as a layer (not sole guard), sensitive-data minimization, user data controls, retention/deletion, consent for memory, provider data handling review.
- Reliability: startup config validation, readiness checks, durable async jobs, database migrations/index checks, retry/backoff with jitter, graceful shutdown, tested restore and provider failover.
- Release controls: CI gates, staging + canary, feature flags, rollback, dependency and container scanning, SBOM, pinned artifacts, incident playbooks.

## Ordered productionization plan

### Gate 0 — Contain tenant risk

1. Verify current deployment/gateway protections immediately; do not assume CORS protects data.
2. Add backend JWT verification and principal-derived IDs to every user endpoint.
3. Add ownership predicates to every session read/write/delete and every memory operation.
4. Remove or strongly protect memory cleanup, detailed context, metrics, and provider-probe endpoints.
5. Replace CORS substring logic with exact production allowlist and tests.

### Gate 1 — Correctness and operational baseline

1. Eliminate `default` session fallback; switch to UUID/ULID session IDs and idempotent turn writes.
2. Make persistence outcome explicit; no silent success on lost chat history.
3. Enforce payload limits, user quotas, deadlines and model output caps.
4. Make production configuration fail closed; make readiness reflect critical dependencies.
5. Add durable queue for memory updates and user controls to inspect/delete stored memory.

### Gate 2 — RAG reliability and measurable quality

1. Document the exact active chat/RAG path; integrate the intended RAG pipeline or remove misleading dead code/claims.
2. Durable index + ingestion lifecycle, ACLs, source/version metadata, deletions and reindex process.
3. Gold-set retrieval/answer evaluation and CI regression thresholds.
4. Hybrid retrieval + reranker + calibrated abstention + verified citations; adversarial document-injection tests.

### Gate 3 — Production engineering

1. Reproducible frontend/backend installs and CI: lint, typecheck, build, unit, integration, auth/tenant security, E2E, dependency scan.
2. Structured privacy-aware tracing/metrics, SLOs and alerts; load/soak tests and cost budgets.
3. Backups and restore drills, migration strategy, data retention/deletion workflows, incident response and rollback.
4. Staging/canary release with feature flags and provider/model/index version pinning.

## Verification notes and limitations

- `npm run lint`: failed because `eslint` was not installed/on PATH (`sh: eslint: command not found`).
- `python -m pytest backend/tests -q`: could not start because the active Python environment has no `pytest` module. This is an environment setup blocker, not a failing test assertion.
- Separate read-only backend and frontend audits corroborated the tenant-isolation and CORS findings and added the admin telemetry, frontend auth-config, onboarding persistence, routed-session, UX error handling, keep-warm, accessibility and clipboard feedback findings above.
- Static review of the current working tree only; no source changes made. The large existing diff makes branch-vs-working-tree attribution difficult and this report treats the inspected working tree as the target.
- External gateway/auth configuration, environment variables, deployment settings, live database ACLs, and production network exposure were not verifiable from the repository.
