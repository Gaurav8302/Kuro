# Memory System v2 — Migration Notes

## Overview
The memory system has been refactored from a complex 3-layer progressive-summarization 
architecture to a minimal, deterministic 2-layer design.

**Root cause of the session-memory-breaking-at-message-5-6 bug:** The old system's 
`RollingMemoryManager` had a `short_term_window=20` setting, but `context_rehydrator.py` 
was capping context at 2000 tokens and injecting FACTS/SUMMARIES blocks that consumed 
most of the token budget. Progressive summarization was also triggering mid-session, 
replacing raw messages with lossy summaries. The combination caused context degradation 
around message 5-6.

---

## What Changed

### New Files (ADD)
| File | Purpose |
|------|---------|
| `memory/session_memory.py` | Layer 1 — fetches last N raw messages from MongoDB |
| `memory/context_builder.py` | Builds clean LLM prompt: system + history + user message |
| `memory/long_term_memory.py` | Layer 2 — post-session summarization + Pinecone retrieval |
| `memory/model_lock.py` | Session-level model locking to prevent drift |
| `memory/chat_manager_v2.py` | New chat manager using the above modules |
| `MIGRATION_NOTES.md` | This file |

### Modified Files (EDIT)
| File | Change |
|------|--------|
| `chatbot.py` | Import `chat_manager_v2` instead of old `chat_manager`; updated `/chat` endpoint |

### Safe to Delete (REMOVE)
These files are no longer imported by the active code path. They can be safely 
removed or archived. The old `chat_manager.py` is kept as a reference but no 
longer imported.

| File | Reason |
|------|--------|
| `memory/rolling_memory.py` | Progressive summarization removed |
| `memory/context_rehydrator.py` | Replaced by `context_builder.py` |
| `memory/memory_recall.py` | Recall logic now in `long_term_memory.py` |
| `memory/memory_trigger.py` | Trigger detection now in `long_term_memory.py` |
| `memory/summarization_prompts.py` | No progressive summarization |
| `memory/layered_summarization_prompts.py` | No layered summaries |
| `memory/pseudo_learning.py` | Corrections system removed from core path |
| `memory/chat_manager.py` | Replaced by `chat_manager_v2.py` |

### MongoDB Collections
| Collection | Status |
|------------|--------|
| `chat_sessions` | **KEEP** — still the primary message store |
| `session_titles` | **KEEP** — now also stores `model_id` for model locking |
| `conversation_summaries` | **SAFE TO DROP** — no longer written to |
| `users` | **KEEP** — user profiles (name, intro_shown) |

### Pinecone
- Old vectors (type=`long_term_summary`, `layered_summary`, `verbatim_fact`, `chat_exchange`) 
  are orphaned but harmless. They can be cleaned up by filtering on metadata `summary_type`.
- New vectors use metadata `summary_type="session_summary"` exclusively.

---

## What Was Removed

| Feature | Why |
|---------|-----|
| `RollingMemoryManager` | Progressive summarization caused mid-session context loss |
| Layered summaries (medium-term) | Added complexity without improving recall |
| Chunk hashing | Unnecessary with single-summary model |
| Fact extraction pipeline | Injected noisy FACTS blocks that displaced real context |
| Importance scoring | Heuristic that didn't improve relevance |
| Dual summarization (legacy + layered) | Doubled LLM costs for marginal benefit |
| Token trimming heuristics | Replaced by simple "trim oldest if > model limit" |
| Memory-per-exchange storage in Pinecone | Every chat stored as vector → noise explosion |
| RAG pipeline integration in chat path | Moved to explicit retrieval endpoints only |
| Pseudo-learning / corrections in chat path | Can be re-added as optional feature later |

---

## Architecture (v2)

```
┌──────────────────────────────────────────────────────────┐
│                      /chat endpoint                       │
│                      (chatbot.py)                         │
└───────────────────────────┬──────────────────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │  chat_manager_v2.py  │
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                  │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼───────┐
   │ context_    │  │ model_lock  │  │   session_    │
   │ builder.py  │  │   .py       │  │   memory.py   │
   └──────┬──────┘  └─────────────┘  └───────┬───────┘
          │                                    │
   ┌──────▼──────┐                      ┌─────▼──────┐
   │ long_term_  │                      │  MongoDB   │
   │ memory.py   │                      │ chat_sessions│
   └──────┬──────┘                      └────────────┘
          │
   ┌──────▼──────┐
   │  Pinecone   │
   │  (summaries)│
   └─────────────┘
```

### Context Building Flow
```
build_context(session_id, user_id, new_message)
  │
  ├─ 1. Fetch last 15 exchanges from MongoDB (session_memory)
  │     → sorted ascending by sequence_number
  │     → returned as [{"role": "user", "content": ...}, {"role": "assistant", ...}]
  │
  ├─ 2. Check long-term memory trigger
  │     → phrase match: "last time", "remember when", "we talked about", etc.
  │     → if triggered: query Pinecone for session summaries (score ≥ 0.85)
  │
  ├─ 3. Assemble messages:
  │     [system_prompt + optional_past_context]  ← system message
  │     [history_msg_1, history_msg_2, ...]      ← raw conversation
  │     [new_user_message]                       ← current turn
  │
  └─ 4. Token check: if total > 28000, trim oldest non-system messages
```

### Model Locking Flow
```
resolve_model(session_id, user_message, router_pick)
  │
  ├─ session.model_id is NULL? → assign router_pick, lock it
  │
  ├─ session.model_id exists?
  │   ├─ user requests code explicitly? → override to code model
  │   ├─ user requests reasoning?       → override to reasoning model
  │   ├─ context > model token limit?   → override to larger model
  │   └─ otherwise                      → reuse locked model
  │
  └─ returns: {model_id, source, locked, override_reason}
```

---

## Rollback Plan
If issues arise:
1. In `chatbot.py`, change the import back to `from memory import chat_manager`
2. The old `chat_manager.py` is untouched and still functional.
3. All old memory modules remain in place (just unused).

---

## Environment Variables (New)
| Variable | Default | Purpose |
|----------|---------|---------|
| `MAX_CONTEXT_TOKENS` | `28000` | Token budget for context window |
| `SESSION_EXCHANGE_LIMIT` | `15` | Max exchanges to fetch per request |
| `POST_SESSION_SUMMARY_THRESHOLD` | `50` | Exchange count that triggers post-session summary |
