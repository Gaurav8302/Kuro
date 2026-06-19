# Kuro AI — Memory Retrieval Engine

## Purpose

The Retrieval Engine is the read-side counterpart to the Extractor. Given a user message, it finds, scores, ranks, and injects the most useful memories into the prompt — while actively avoiding context pollution from irrelevant or low-value information.

---

## 1. Retrieval Pipeline

```
User Message
    │
    ▼
┌────────────────────────────┐
│ Stage 1: Trigger Decision   │
│ Should we retrieve at all?  │
└──────────┬─────────────────┘
           │ yes
           ▼
┌────────────────────────────┐
│ Stage 2: Query Rewriting   │
│ Enhance query for search   │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Stage 3: Multi-Store Query │
│ Parallel search across     │
│ Episodic / Semantic / Pref │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Stage 4: Fusion & Ranking  │
│ Score candidates using:    │
│ score = I × R × S × T     │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Stage 5: Selection & Trim  │
│ Pick top-N, stay in budget │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ Stage 6: Injection         │
│ Place into prompt context  │
└────────────────────────────┘
```

---

## 2. Stage 1: Trigger Decision

Not every message needs memory retrieval. Retrieving when unnecessary wastes tokens and adds noise.

### Decision Rules

| Condition | Action | Rationale |
|-----------|--------|-----------|
| Greeting (< 8 words, greeting keywords) | Skip | "Hi, how are you?" needs no memory |
| First message in session | Skip | No context to retrieve against |
| User explicitly asks "remember..." | Full retrieval (all types, top_k=12) | High recall needed |
| User asks "what do you know about me" | Full retrieval + list format | User wants introspection |
| Message has personal pronouns (I, my, me, we, our) | Retrieve semantic + preference | Likely self-referential |
| Message has past tense about user | Retrieve episodic | Likely about past events |
| Message has recall keywords (remember, before, last time) | Retrieve all types | Explicit recall request |
| Message is technical (code, debugging) | Retrieve semantic only (facts) | Preferences/events less useful |
| General conversation (12+ words, no personal refs) | Light retrieval (top_k=3) | Shallow check, avoid over-injection |
| Short casual (< 8 words, no keywords) | Skip | Not worth the context |

### Implementation

A fast decision tree — single pass, regex-based, sub-millisecond. No LLM call.

```
SHOULD_RETRIEVE:
    if is_greeting(MSG) and len(MSG) < 8: return (False, "greeting")
    if is_first_turn(SESSION): return (False, "first_turn")
    if has_recall_keywords(MSG): return (True,  "recall_explicit", ALL_TYPES, top_k=12)
    if has_personal_pronouns(MSG): return (True, "self_referential", [SEMANTIC, PREFERENCE], top_k=6)
    if has_past_tense(MSG): return (True, "past_event", [EPISODIC, SEMANTIC], top_k=6)
    if is_technical(MSG): return (True, "technical", [SEMANTIC], top_k=4)
    if len(MSG) >= 12: return (True, "long_message", [SEMANTIC, PREFERENCE], top_k=3)
    return (False, "casual_skip")
```

Estimated skip rate: 40-50% of turns avoid retrieval entirely.

---

## 3. Stage 2: Query Rewriting

The raw user message is often a poor search query. "What was that project I built?" needs to be rewritten for embedding search.

### Rewriting Rules

| Raw message | Rewritten query |
|---|---|
| "What was that project I built?" | "project user built" |
| "Do you remember what I like?" | "user preferences likes" |
| "You told me about some AI thing" | "AI user discussed" |
| "I need help with Python" | "user Python knowledge" |
| No change needed (explicit, specific) | Use verbatim |

### Strategy

- Strip question words, recall framing, polite preambles
- Extract noun phrases and domain terms
- Prefix with "user" to bias toward user-centric memories
- Keep under 50 characters for embedding focus

The rewriter uses simple regex rules. No LLM call. Estimated 10x faster than LLM-based rewriting.

---

## 4. Stage 3: Multi-Store Query

Three parallel queries, one per memory type.

```
FOR EACH memory_type IN trigger_decision.types:

    candidates[memory_type] = store.search(
        query=rewritten_query,
        memory_type=memory_type,
        user_id=current_user,
        top_k=top_k * 2,  // Retrieve more than needed; ranking will trim
        min_confidence=0.50  // Skip low-confidence items at the source
    )

merge all candidates into a flat list
```

Each store implements its own search:

| Store | Algorithm | Notes |
|-------|-----------|-------|
| Episodic | Embedding cosine + temporal filter | Boost recent events slightly |
| Semantic | Embedding cosine + importance filter | Prefer high-importance facts |
| Preference | Embedding cosine + category match | Boost if category overlaps |

---

## 5. Stage 4: Fusion & Ranking

The core of the engine. Every candidate memory receives a `retrieval_score` that determines whether it enters the prompt.

### The Formula

```
retrieval_score = importance × relevance × recency × type_boost
```

Each factor is normalized to [0.0, 1.0] so the product stays in [0.0, 1.0].

#### Factor 1: Importance (I)

Already stored with the memory (1.0–10.0). Normalized:

```
importance_normalized = memory.importance / 10.0
```

| Raw importance | Normalized | Meaning |
|---|---|---|
| 1.0–3.0 | 0.10–0.30 | Low significance (transient, vague) |
| 4.0–6.0 | 0.40–0.60 | Moderate (useful but not critical) |
| 7.0–8.0 | 0.70–0.80 | High (core facts about user) |
| 9.0–10.0 | 0.90–1.00 | Critical (identity, long-term projects) |

#### Factor 2: Relevance (R)

Cosine similarity between the rewritten query's embedding and the memory's embedding.

```
relevance = cosine_similarity(query_embedding, memory_embedding)
relevance ∈ [0.0, 1.0]
```

| Cosine score | Meaning |
|---|---|
| 0.00–0.25 | Unrelated (filter out) |
| 0.26–0.50 | Loosely related |
| 0.51–0.75 | Moderately relevant |
| 0.76–1.00 | Highly relevant |

#### Factor 3: Recency (R² — time decay)

Exponential decay based on how long ago the memory was created.

```
days_old = (now - memory.timestamp).days

recency = 0.5 ^ (days_old / decay_halflife)
```

| Decay halflife | Category | Rationale |
|---|---|---|
| 14 days | Episodic | Events become less relevant quickly |
| 60 days | Semantic | Facts are relatively stable |
| 30 days | Preference | Preferences drift over time |

| Age | Episodic (14d) | Semantic (60d) | Preference (30d) |
|-----|----------------|----------------|-------------------|
| 0 days | 1.00 | 1.00 | 1.00 |
| 7 days | 0.71 | 0.92 | 0.85 |
| 30 days | 0.23 | 0.71 | 0.50 |
| 90 days | 0.01 | 0.35 | 0.12 |
| 180 days | 0.00 | 0.12 | 0.02 |

#### Factor 4: Type Boost (T)

Multiplicative boost based on whether the memory type matches the trigger context.

| Trigger | Episodic boost | Semantic boost | Preference boost |
|---------|---------------|----------------|------------------|
| "remember when" | 1.3 | 1.0 | 1.0 |
| "what do you know" | 1.0 | 1.2 | 1.2 |
| "I like / prefer" | 1.0 | 1.0 | 1.4 |
| Technical | 1.0 | 1.3 | 0.8 |
| "what is my" | 0.8 | 1.3 | 1.1 |
| Default | 1.0 | 1.0 | 1.0 |

### Complete Worked Example

```
Memory: "User built a project called TabMind using Python"
Type: episodic
Importance: 8.0 → normalized 0.80
Relevance to query "project user built": cosine = 0.91
Age: 45 days old
Recency (episodic halflife=14d): 0.5^(45/14) = 0.5^3.21 = 0.11
Trigger: recall_explicit → episodic boost = 1.3 (no, this actually doesn't matter much, let's use a different value)

Wait, let me recalculate more carefully.

Score = I × R × R² × T

= 0.80 × 0.91 × 0.11 × 1.0
= 0.08

This is low because the event is 45 days old. That's correct behavior — very old episodic
memories should not surface unless highly relevant.

Now consider a semantic memory from the same user:

Memory: "User knows Python"
Type: semantic
Importance: 7.5 → normalized 0.75
Relevance to query: cosine = 0.85
Age: 100 days old
Recency (semantic halflife=60d): 0.5^(100/60) = 0.5^1.67 = 0.31
Trigger: technical → semantic boost = 1.3

Score = 0.75 × 0.85 × 0.31 × 1.3 = 0.26

Higher than the episodic memory — correct, because semantic facts about Python skills
are more useful for a technical query than an old event.

Now a preference:

Memory: "User prefers fast APIs"
Type: preference
Importance: 6.0 → normalized 0.60
Relevance to query: cosine = 0.45 (only moderately related)
Age: 10 days
Recency (preference halflife=30d): 0.5^(10/30) = 0.79
Trigger: technical → preference boost = 0.8

Score = 0.60 × 0.45 × 0.79 × 0.8 = 0.17

Rightfully lower — the preference is weakly related to the query.
```

### Filter Threshold

Any memory with `retrieval_score < 0.10` is discarded. This prevents near-zero-score memories from consuming context.

| Score Range | Action |
|---|---|
| 0.00 – 0.09 | Discard (noise) |
| 0.10 – 0.29 | Include only if context budget permits (last resort) |
| 0.30 – 0.59 | Include in middle tier |
| 0.60 – 1.00 | High priority (injected first) |

---

## 6. Stage 5: Selection & Context Budget

### Hard Limits

| Constraint | Value | Rationale |
|---|---|---|
| Max memories injected | 8 | Beyond this, quality degrades and token cost climbs |
| Max tokens for memory section | 800 tokens (~3200 chars) | ~5% of a 16K context window |
| Min retrieval score | 0.10 | Below this is noise |
| Max per memory type | 4 of any single type | Prevent type dominance |
| Recency floor | 0.01 | Memories older than 7 halflives effectively excluded |

### Selection Algorithm

```
1. Sort all candidates by retrieval_score (descending)
2. Filter out scores < 0.10
3. Apply type diversity constraint (max 4 per type)
4. Take top 8
5. Truncate memory texts to fit in 800-token budget
   - Longest memories trimmed first
   - If still over budget, drop lowest-scored memory
6. Return final list
```

### Type Diversity

Without diversity enforcement, a strongly related semantic memory could dominate all 8 slots. This ensures at least some variety:

```
Example result:
  3 episodic  (top scores: 0.45, 0.38, 0.30)
  3 semantic  (top scores: 0.52, 0.41, 0.22)
  2 preference (top scores: 0.35, 0.28)
```

---

## 7. Stage 6: Memory Injection

Memories are injected into the prompt as a structured block.

### Format

```
Relevant context about you:

[memory 1 content] (confidence: high)
[memory 2 content] (confidence: medium)
[memory 3 content] (confidence: high)

---

[user message continues...]
```

### Position

Injected between the system prompt and the chat history, immediately before the user message. This position lets the LLM see the memories as context before reading the current query.

### Confidence Label

Each memory is tagged with a human-readable confidence label so the LLM can weigh it appropriately:

| Confidence | Label | LLM behavior |
|---|---|---|
| 0.90–1.00 | `very high` | Treat as confirmed fact |
| 0.70–0.89 | `high` | Treat as likely true |
| 0.50–0.69 | `medium` | Treat as possible, verify if critical |
| < 0.50 | (not retrieved) | — |

### Injection Example in Prompt

```
System: You are Kuro, a friendly AI assistant.

Relevant context about you:
- You built a project called TabMind using Python (confidence: high)
- You study computer science (confidence: very high)
- You prefer local AI models (confidence: medium)

Chat History:
User: Hi
Kuro: Hello!

User:
What do you remember about my projects?
```

---

## 8. Context Pollution Prevention

Context pollution happens when irrelevant or low-value memories are injected, diluting the signal-to-noise ratio in the prompt.

### Prevention Mechanisms

| Mechanism | What it prevents | How |
|-----------|------------------|-----|
| Trigger decision | Unnecessary retrieval | 40-50% of turns skip entirely |
| Score threshold | Low-relevance memories | Hard floor at 0.10 |
| Type diversity | Single-type dominance | Max 4 per type |
| Token budget | Overflow | Hard cap at 800 tokens |
| Min confidence | Uncertain memories | Don't store < 0.50, don't retrieve < 0.50 |
| Recency halflife | Stale episodic noise | Exponential decay, effectively excludes very old events |
| Working memory overlap | Duplication of current session | Dedup against working buffer before injection |

### Working Memory Deconflict

Before injecting retrieved memories, check the working memory buffer (current session turns). If a memory directly repeats something already visible in the recent chat history, suppress it:

```
IF memory.content overlaps working_buffer (jaccard > 0.7):
    SUPPRESS  // Already in context via recent chat
```

This prevents the LLM from seeing "User built TabMind" in both the memory section and the last 3 turns of chat history.

---

## 9. Failure Cases

### Case 1: Empty Store (Cold Start)

**Problem**: User is new, no memories exist. Retrieval returns zero results.

**Behavior**: Pipeline short-circuits at Stage 3. No memory section is added to the prompt. The LLM responds based on system prompt + chat history alone.

**Detection**: `len(candidates) == 0` after Stage 3. Log as `retrieval_empty` metric.

### Case 2: All Candidates Below Threshold

**Problem**: Memories exist but none score ≥ 0.10 (e.g., user asked about cooking but only stored memories are about programming).

**Behavior**: Same as empty store. No memory injection. No harm done.

**Distinction**: Log as `retrieval_below_threshold` (vs `retrieval_empty`). Important for monitoring whether the embedding model captures query intent.

### Case 3: Query Embedding Failure

**Problem**: Embedding API (Gemini) is down or returns an error.

**Behavior**: Fall back to keyword-only retrieval. Tokenize query, search by Jaccard overlap on memory content. This is less accurate but better than nothing.

**Degradation**: Keyword-only retrieval has ~60% of the recall of embedding-based search. Log the fallback.

### Case 4: Storage Backend Unavailable

**Problem**: JSON file locked, corrupted, or I/O error.

**Behavior**: Fail open. Skip retrieval entirely, respond without memory. Log the error for monitoring. Do NOT crash the chat endpoint.

### Case 5: Memory Flood (Too Many High-Scoring Memories)

**Problem**: Query is very broad ("tell me about myself") and 40+ memories score above threshold.

**Behavior**: Selection algorithm handles this — top 8 with type diversity. The type cap (4 per type) prevents semantic memories from dominating. The rest are silently dropped.

**Metrics**: Track how many candidates were dropped due to type cap and budget cap. High drop rates suggest the user needs memory pruning.

### Case 6: Contradictory Memories Retrieved

**Problem**: Both "User prefers VS Code" and "User prefers Neovim" are retrieved.

**Behavior**: Both are injected. The confidence labels help the LLM: if "VS Code" has confidence 0.90 and "Neovim" has 0.55, the LLM can weigh them. The LLM should handle mild contradictions naturally.

**Long-term fix**: The Update Pipeline should detect contradictions and decay the older/less-confident item.

### Case 7: Session Boundary Leak

**Problem**: User starts a new session about a completely different topic (e.g., was coding last session, now asking about cooking).

**Behavior**: Old memories are retrieved but have low relevance to the new query. The relevance factor (cosine similarity) naturally suppresses them. Only memories that happen to be semantically related to "cooking" would surface.

---

## 10. Full Worked Example

### Turn 45, Session 2

```
User: "Hey, I'm thinking about building another project like TabMind.
       Do you remember what stack I used?"
```

**Stage 1 — Trigger Decision**:
- Has recall keywords ("do you remember")
- Has past tense ("I used")
- Has personal reference ("I'm", "my")
- Decision: RETRIEVE, all types, top_k=12

**Stage 2 — Query Rewriting**:
- "project user built tech stack"

**Stage 3 — Multi-Store Query**:
- Episodic: "User built TabMind using Python and FastAPI" (cosine: 0.89)
- Semantic: "User knows Python" (cosine: 0.72)
- Semantic: "User works with FastAPI" (cosine: 0.68)
- Preference: "User prefers async frameworks" (cosine: 0.45)
- Episodic: "User switched to local AI models" (cosine: 0.22)
- ... total 14 candidates

**Stage 4 — Ranking**:
```
1. "User built TabMind using Python and FastAPI" | Epi | I=0.80 R=0.89 R²=0.85 T=1.0 | score=0.61
2. "User knows Python"                          | Sem | I=0.75 R=0.72 R²=0.95 T=1.2 | score=0.62
3. "User works with FastAPI"                    | Sem | I=0.70 R=0.68 R²=0.90 T=1.2 | score=0.51
4. "User prefers async frameworks"              | Pref| I=0.60 R=0.45 R²=0.80 T=1.0 | score=0.22
5. "User switched to local AI models"           | Epi | I=0.65 R=0.22 R²=0.60 T=1.0 | score=0.09 ← BELOW THRESHOLD
```

**Stage 5 — Selection**:
- Top 3: TabMind (epi), Python (sem), FastAPI (sem) — all above 0.10
- Type diversity: 1 episodic, 2 semantic. No preference above threshold.
- Under 8-item limit and 800-token budget.
- Final: 3 items injected.

**Stage 6 — Injection**:
```
Relevant context about you:
- You built a project called TabMind using Python and FastAPI (confidence: high)
- You know Python (confidence: very high)
- You work with FastAPI (confidence: high)

---

User: "Hey, I'm thinking about building another project like TabMind..."
```

**Result**: Kuro has all relevant context to answer the user's question about their own project stack.
