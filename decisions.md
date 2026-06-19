# Kuro AI — Architecture Decision Records

## Purpose

Track important technical decisions made during Kuro AI development.

---

## ADR-001

**Date**: 2025-01-27

**Status**: Accepted

**Decision**: Use 4 specialized models (Conversation, Reasoning, Code, Summarization) with deterministic skill-based routing.

**Reason**: Early versions used many models with complex scoring, which was hard to debug and predict. A simplified 1:1 skill-to-model mapping gives faster responses, predictable behavior, and lower costs.

**Alternatives Considered**:
- Single universal model (too slow, poor specialization)
- Score-based dynamic routing (too complex, hard to debug)
- 10+ model pool (over-engineered for current needs)

**Tradeoffs**: Less flexibility in model selection vs simpler, more maintainable codebase.

**Consequences**: Deterministic routing is easy to test and audit. Adding new capabilities requires expanding the skill-to-model mapping rather than tweaking scoring weights.

---

## ADR-002

**Date**: 2025-01-27

**Status**: Accepted

**Decision**: Use Pinecone for long-term vector memory with 384-dim embeddings (downsampled from Gemini's 768-dim).

**Reason**: Pinecone provides managed vector storage with high-performance cosine similarity search. Gemini `text-embedding-004` is cost-effective (free tier sufficient). Downsampling to 384-dim reduces storage costs while maintaining retrieval quality.

**Alternatives Considered**:
- MongoDB Atlas Vector Search (wasn't GA at decision time)
- ChromaDB (self-hosted, more operational overhead)
- FAISS (requires self-managed infrastructure)

**Tradeoffs**: External dependency on Pinecone vs self-managed alternatives. 384-dim downsampling loses some embedding fidelity.

**Consequences**: Semantic memory queries are fast and reliable. Pinecone free tier is sufficient for development. Downsampling has not shown measurable quality degradation.

---

## ADR-003

**Date**: 2025-08-11

**Status**: Accepted

**Decision**: Implement circuit breaker pattern with CLOSED/OPEN/HALF_OPEN states and max 2 fallback models per primary model.

**Reason**: AI providers can fail or rate-limit. Circuit breakers prevent cascading failures and allow automatic recovery. Limiting to 2 fallbacks keeps fallback chains fast and predictable.

**Alternatives Considered**:
- Unlimited retry (causes thundering herd problem)
- No fallback (poor user experience on provider failure)
- Manual failover (requires human intervention)

**Tradeoffs**: Brief service degradation during cooldown vs complete outage without circuit breakers.

**Consequences**: System self-heals from transient provider failures. 60s cooldown is acceptable for production use.

---

## ADR-004

**Date**: 2025-08-11

**Status**: Accepted

**Decision**: 3-layer memory architecture (Short-term raw → Medium-term summaries → Long-term vectors) with progressive summarization.

**Reason**: Single-layer memory doesn't scale. Raw messages consume too many tokens. Summaries lose detail. Vectors enable cross-session recall. Combining all three layers balances quality, cost, and performance.

**Alternatives Considered**:
- Flat message history (token explosion, no long-term recall)
- Only vector memory (loss of recent conversational fidelity)
- Only summarization (fact drift over time)

**Tradeoffs**: More complex implementation vs superior context retention across sessions.

**Consequences**: Memory usage is efficient. Facts are preserved verbatim. Old summaries are gracefully dropped under token budget pressure while facts are never removed.

---

## ADR-005

**Date**: 2025-01-27

**Status**: Accepted

**Decision**: Use shadcn/ui component library with TailwindCSS for the frontend design system.

**Reason**: shadcn/ui provides accessible, customizable, copy-paste components built on Radix primitives. TailwindCSS enables rapid styling without custom CSS. Together they allow a unique holographic design system while maintaining accessibility.

**Alternatives Considered**:
- Material UI (heavy, harder to customize)
- Chakra UI (slower development velocity)
- Ant Design (complex theming)

**Tradeoffs**: Components are copied into the project (no npm dependency updates) vs full control over customization.

**Consequences**: Fast UI development with consistent design. Component customization is straightforward.

---

## ADR-006

**Date**: 2025-08-11

**Status**: Accepted

**Decision**: Use regex-based intent classification rather than ML-based classification for model routing.

**Reason**: Regex classification is deterministic, fast (sub-millisecond), and easy to debug. ML-based classification would add latency, require training data, and be harder to maintain. For the current 4-skill system, regex is sufficient.

**Alternatives Considered**:
- Embedding similarity classification (heavier, over-engineered)
- ML model classification (requires training data and maintenance)
- LLM-based classification (slow and expensive for routing)

**Tradeoffs**: Less flexible for nuanced intents vs fast, predictable, zero-cost routing.

**Consequences**: Routing is fast and transparent. New intent patterns are easy to add as regex rules. Future consideration: add embedding similarity as a fallback for messages without keyword triggers.
