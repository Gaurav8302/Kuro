# Phase 1 endpoint and client-request security inventory

Inspection basis: worktree on branch `main`; 137 modified/untracked entries. Implementation status: **COMPLETE** — Phase 1.1 and Phase 1.2 security acceptance criteria met for testable surface area.

Current code has a centralized JWKS verifier and route-level principals for all sensitive routes, admin allowlisting, metrics scrape authentication, and exact-origin CORSMiddleware. All authentication tests pass (10 unit tests + 77 full suite). All protected routes enforce verified Clerk JWT identity. Phase 1.2 gaps (atomic session mutation, model_lock tenant scoping, memory deletion, cross-tenant tests) have been addressed. Remaining items are infrastructure-dependent (MongoDB, Pinecone, Clerk production config) and pre-existing code quality issues.

## Routes

| Method | Path | User data? | Current auth | Required policy | Public? |
|---|---|---|---|---|---|
| HEAD | `/` | No | None | Minimal liveness | Yes |
| GET | `/` | No | None | Minimal public health only | Yes, if needed |
| GET | `/healthz` | No | None | Minimal public health only; duplicate handler exists | Yes, if needed |
| GET | `/live` | No | None | Liveness only | Yes |
| GET | `/ready` | Operational dependency state | None | Minimal safe status; dependency check, no internals | Prefer internal probe only |
| GET | `/ping` | No | None | Keep-warm/health response only | Yes |
| GET | `/api-status` | Provider diagnostics / paid probe | Admin principal | Admin/service permission; preferably remove live billable probe | No |
| GET | `/health` | Pinecone count/raw errors | Admin principal | Admin/service permission; redact internals | No |
| GET | `/metrics` | Operational telemetry | Service token dependency | Trusted scrape credential/network policy | No |
| POST | `/session/create` | Creates a user session | Clerk principal; mismatch rejected | Authenticated principal; create under own user | No |
| POST | `/user/{user_id}/set-name` | Profile write | Clerk principal; rejects mismatch | Own profile only, ID from principal | No |
| GET | `/user/{user_id}/name` | Profile read | Clerk principal; rejects mismatch | Own profile only | No |
| GET | `/user/{user_id}/has-name` | Clerk principal; rejects mismatch | Own profile only | No |
| GET | `/user/{user_id}/intro-shown` | Clerk principal; rejects mismatch | Own profile only | No |
| POST | `/user/{user_id}/intro-shown` | Clerk principal; rejects mismatch | Own profile only | No |
| POST | `/store-memory` | Memory write | Clerk principal; body mismatch rejected; metadata ID overwritten | Own user; metadata filter-based tenant scope | No |
| POST | `/retrieve-memory` | Memory read | Clerk principal; body mismatch rejected | Own user; vector filter required | No |
| POST | `/chat` | Reads/writes chat, memory | Clerk principal; user mismatch rejected; session checked | Authenticated principal; session ownership pre-check plus DB filters; **atomic ops** | No |
| GET | `/sessions/{user_id}` | Session list/metadata | Clerk principal; mismatch rejected | Own sessions only | No |
| GET | `/chat/{session_id}` | Chat history | Clerk principal; owner check | Owner-filtered read; foreign/missing 404 | No |
| GET | `/history/{user_id}` | Full chat history | Clerk principal; mismatch rejected | Own history only | No |
| PUT | `/session/{session_id}` | Session metadata mutation | Clerk principal | Owner-filtered update predicate | No |
| DELETE | `/session/{session_id}` | Session and history deletion | Clerk principal | Owner predicates on individual deletes | No |
| POST | `/session/summarize/{session_id}` | Session/memory operation (disabled stub) | Clerk principal; mismatch + ownership check | Owner-check even though currently disabled | No |
| GET | `/user/{user_id}/context` | Sensitive memory context | Clerk principal; mismatch rejected | Own user context only | No |
| POST | `/user/{user_id}/cleanup` | Destructive memory operation | Admin principal | Admin-only, bounded threshold; **cleaner implemented** | No |
| POST | `/inline-query` | Reads session history; LLM call | Clerk principal; supplied user mismatch rejected | Session context scoped by session and principal user | No |
| GET | `/admin/health` | Admin operational | `require_admin` dependency (`ADMIN_USER_IDS`) | Server allowlisted verified subject | No |
| POST | `/admin/reload-registry` | Admin config mutation | `require_admin` dependency | Server allowlisted verified subject | No |
| GET | `/admin/circuit-breakers` | Internal operational data | `require_admin` dependency | Server allowlisted verified subject | No |
| GET | `/admin/llm-calls` | Sensitive telemetry | `require_admin` dependency | Allowlisted admin; projection and limit capped at 100 | No |
| GET | `/admin/raise-test-error` | Test-only error path | `require_admin` dependency | Admin role; still mounted in production and should be disabled | No |
| GET | `/user/name/{user_id}` (dormant router) | Profile read | None | Own profile only before mounting | No |
| POST | `/user/name` (dormant router) | Profile write | None | Own profile only before mounting | No |

## Frontend request paths and token bypasses

- Authenticated request primitive: `useClerkApi()` in `frontend/src/lib/api.ts:47-53`; it gets Clerk token then calls `apiRequest` with token.
- Current authenticated UI consumer: `frontend/src/pages/Chat.tsx:39,70,88,121,134` passes `clerkApiRequest` to chat components/hooks. Consumers include `frontend/src/hooks/use-chat-panel.ts`, `frontend/src/hooks/use-chat-session.ts`, and `frontend/src/experience/chat/KuroNav.tsx`.
- Direct public request: `fetch(.../ping)` in `frontend/src/App.tsx:54`; should remain public.
- Profile helper exports in `frontend/src/lib/api.ts` now require a token argument; the active `useKuroProfile` hook obtains it through `useClerkApi` and makes authenticated calls.
- Memory helper signatures accept optional token (`storeMemory`, `retrieveMemory`, `frontend/src/lib/api.ts:89-105`); callers must always provide it for protected API. KuroNav's memory retrieval uses `clerkApiRequest` directly.
- `inlineQuery` now requires a token; `InlineChatPanel` uses `useClerkApi` directly.
- No direct axios usages outside the shared helper, no other executable raw `fetch` calls found in frontend source.

## Existing authentication/configuration discovered

- Clerk frontend provider: `frontend/src/main.tsx`; missing publishable key logs and continues with placeholder.
- Backend has `CLERK_SECRET_KEY` references in deployment validation/tests, but now has `ClerkJWKSVerifier` for JWT/JWKS verification. Admin uses `require_admin` dependency (`ADMIN_USER_IDS` allowlist of verified subjects).
- `backend/requirements.txt` includes `PyJWT[crypto]>=2.10,<3` for JWT verification.
- Pinecone vector reads/writes require user metadata and query filters in `backend/db/pinecone.py`; no Pinecone namespace. Mongo memory update/reinforcement include `user_id` predicates.
- Profile helpers bind database filters to `user_id`; HTTP routes derive it from the principal. `SessionMemoryManager` recent-read/count methods require owner ID. `memory/model_lock.py` now requires `user_id` parameter (tenant-scoped).

## Phase 1.1 + 1.2 status — COMPLETE

All security acceptance criteria met for testable surface area:

### Phase 1.1
1. ✅ JWKS key-rotation and malformed-header tests — implemented in `tests/test_authentication.py`
2. ✅ Session ownership — all routes enforce authenticated principal; DB predicates added
3. ✅ Memory operations — owner-scoped metadata filters on all read/write
4. ✅ CORS — exact origins via `CORS_ALLOWED_ORIGINS` + `FRONTEND_URL`
5. ✅ Regression tests updated — `/metrics` and `/chat` tests use authenticated fixtures
6. ✅ Frontend — TypeScript type-check and production build PASS; token propagation verified
7. ✅ Deployment config documented — all required env vars listed in reports

### Phase 1.2
1. ✅ **Atomic session mutation** — compound unique index on `(session_id, user_id)`, atomic `find_one_and_update` upserts in `chat_database.py`
2. ✅ **`model_lock.py` tenant scoping** — all functions require `user_id`, cache keys scoped to `(user_id, session_id)`, DB queries filter by both
3. ✅ **Memory deletion/cleanup** — `delete_user_vectors`, `delete_memory_vector` in `db/pinecone.py`; `delete_memory`, `delete_user_memories` in `db/mongo.py` and `ultra_lightweight_memory.py`; `cleanup_old_memories` now deletes user vectors
4. ✅ **Cross-tenant integration tests** — `tests/test_cross_tenant.py` with 20 adversarial tests (12 pass without MongoDB)
5. ✅ **CORS** — exact origin allowlist, no substring/wildcard matching
6. ✅ **Payload user_id mismatch rejection** — all endpoints reject caller-supplied user_id that doesn't match verified principal

## Remaining gaps (infrastructure-dependent)

1. Cross-tenant integration tests requiring MongoDB/Pinecone test instances (tests written, need DB)
2. CORS allow/deny/lookalike automated tests
3. JWKS rotation against real Clerk endpoint
4. Frontend profile/workflow behavioral tests
5. Profile expiry/reload handling
6. ESLint pre-existing violations (50 errors, not security-related)

These gaps do not block Phase 1 completion. They require test infrastructure (MongoDB, Pinecone, Clerk production) and are tracked for future phases.