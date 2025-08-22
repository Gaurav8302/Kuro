# Layered Memory & Progressive Summarization

## Objectives
- Preserve conversational fidelity over long horizons while controlling token footprint.
- Retain high-signal immutable facts (user profile facts, explicit preferences, commitments).
- Provide deterministic, auditable compression path (original → layered summaries + fact blocks).

## Layers
| Layer | Source | Retention | Purpose |
|-------|--------|-----------|---------|
| Short-Term Window | Recent raw turns | Sliding (N last exchanges) | Local coherence & immediate follow-ups |
| Medium Summary | Aggregated short-term batches | Rolling updates | Mid-session continuity |
| Long Summary | Aggregated medium summaries | Sparse evolution | Persistent narrative arc |
| Verbatim Facts | Extracted during summarization | Append-only (dedup) | Critical truth anchors |

## Key Modules
| Module | Path | Function |
|--------|------|----------|
| Rolling Memory Manager | `backend/memory/rolling_memory.py` | Ingest turns, trigger summarization layers, extract facts |
| Layered Prompt Templates | `backend/memory/layered_summarization_prompts.py` | Deterministic structured summarization prompts |
| Context Rehydrator | `backend/memory/context_rehydrator.py` | Assemble prompt context under token budget |
| Ultra Lightweight Memory | `backend/memory/ultra_lightweight_memory.py` | Vector semantic retrieval (summaries + facts) |

## Summarization Strategy
1. Collect raw turns until threshold (e.g. 8–10).
2. Generate medium-layer summary + verbatim fact candidates.
3. Periodically fold medium summaries into a long-layer synthesis when count/size threshold reached.
4. Store original raw blocks alongside structured derivatives (audit & potential re-summarization).

### Fact Extraction
- Pattern-seeking prompt sections isolate: preferences, biographical tidbits, goals, constraints.
- Deduplicated case-insensitively; conflicts flagged for future resolution logic.

## Context Assembly Order
1. Facts (authoritative anchors)
2. Layered summaries (broad situational context)
3. Recent raw turns (fine-grained dialogue state)

Token budgeting trims from lowest priority within same tier (oldest summaries first) before touching facts.

## Deduplication
- Facts: normalized lower-case string match.
- Summaries: hashed first 120 chars to avoid accidental duplication.

## Auditability
Each compression step retains a reference to the original raw slice enabling:
- Regeneration with improved prompts.
- Drift detection (semantic comparison future).

## Edge Cases Handled
- Empty history → graceful empty context.
- Token overflow → iterative rebuild with progressive removal.
- Corrupted memory entry → skipped with log warning.
- User opt-out / forget request → planned redaction pipeline (placeholder).

## Extension Ideas
- Semantic diffing before accepting new long summary (avoid redundancy).
- Bloom filter for fast duplicate fact detection at scale.
- Consistency checker comparing facts vs new summaries for divergence.

---
Efficient, layered, and resilient—built to scale conversational continuity without runaway token costs.
