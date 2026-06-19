# Kuro AI — Memory Architecture v2

## Purpose

Replace the current 3-layer memory (short/medium/long-term) with a 4-layer cognitive memory architecture inspired by human memory models: Working, Episodic, Semantic, and Preference. Local-first, JSON-backed, upgradeable to SQLite.

---

## 1. Architecture Overview

### The Four Memory Layers

```
┌─────────────────────────────────────────────────────┐
│                  WORKING MEMORY                      │
│  (In-memory, ephemeral, current session only)        │
│  Like RAM: fast, volatile, sliding window of turns   │
├─────────────────────────────────────────────────────┤
│                 EPISODIC MEMORY                       │
│  (JSON persistence, event-oriented)                  │
│  "User built TabMind", "User switched to local AI"   │
├─────────────────────────────────────────────────────┤
│                 SEMANTIC MEMORY                       │
│  (JSON persistence, fact-oriented)                   │
│  "User studies computer science"                     │
├─────────────────────────────────────────────────────┤
│                PREFERENCE MEMORY                      │
│  (JSON persistence, preference-oriented)             │
│  "User prefers local AI models"                      │
└─────────────────────────────────────────────────────┘
```

### Layer Characteristics

| Property | Working | Episodic | Semantic | Preference |
|----------|---------|----------|----------|------------|
| Duration | Session | Months | Months | Months |
| Storage | RAM | JSON file | JSON file | JSON file |
| Size cap | 50 turns | Unlimited | Unlimited | Unlimited |
| Persistence | None | File | File | File |
| Query method | Exact match | Semantic + temporal | Semantic | Semantic |
| Confidence | N/A | Yes | Yes | Yes |
| Dedup | N/A | Yes | Yes | Yes |

---

## 2. Folder Structure

```
backend/
└── memory_v2/
    ├── __init__.py
    ├── config.py                  # Tunable constants
    ├── types.py                   # Data classes / type definitions
    │
    ├── working/
    │   ├── __init__.py
    │   └── buffer.py              # In-memory sliding window
    │
    ├── episodic/
    │   ├── __init__.py
    │   ├── store.py               # CRUD for episodic memory
    │   └── schema.json            # JSON schema
    │
    ├── semantic/
    │   ├── __init__.py
    │   ├── store.py               # CRUD for semantic memory
    │   └── schema.json            # JSON schema
    │
    ├── preference/
    │   ├── __init__.py
    │   ├── store.py               # CRUD for preference memory
    │   └── schema.json            # JSON schema
    │
    ├── pipelines/
    │   ├── __init__.py
    │   ├── extractor.py           # Extraction pipeline (conversation → memories)
    │   ├── retriever.py           # Retrieval pipeline (query → context)
    │   └── updater.py             # Update pipeline (merge, reinforce, decay)
    │
    ├── core/
    │   ├── __init__.py
    │   ├── confidence.py          # Confidence scoring
    │   ├── dedup.py               # Duplicate detection
    │   ├── embedding.py           # Embedding interface
    │   └── storage.py             # Abstract storage backend (JSON / SQLite)
    │
    └── data/                       # JSON data files (gitignored except schemas)
        ├── episodic.json
        ├── semantic.json
        └── preference.json
```

### Storage Abstraction

The `core/storage.py` provides a `StorageBackend` interface:

```
StorageBackend (abstract)
├── JsonStorage         # Current: file-based, load/save entire file
└── SqliteStorage       # Future: SQLite with proper indexing
```

Both implement: `load()`, `save()`, `query()`, `transaction()`.

This means the three `store.py` files never touch JSON directly — they go through the backend. When upgrading from JSON to SQLite, only `core/storage.py` changes.

---

## 3. JSON Schemas

### episodic.json

```json
{
  "version": 1,
  "user_id": "user_abc123",
  "items": [
    {
      "id": "epi_01j4...",
      "type": "episodic",
      "content": "User built a project called TabMind",
      "confidence": 0.92,
      "importance": 7.5,
      "timestamp": "2026-03-15T14:30:00Z",
      "session_id": "sess_xyz",
      "source_turn": 12,
      "context": {
        "verb": "built",
        "object": "TabMind",
        "subject": "User",
        "temporal_marker": "2026-03-15"
      },
      "tags": ["project", "development"],
      "access_count": 3,
      "last_accessed": "2026-06-18T10:00:00Z",
      "created_at": "2026-03-15T14:30:00Z",
      "updated_at": "2026-06-18T10:00:00Z"
    }
  ]
}
```

### semantic.json

```json
{
  "version": 1,
  "user_id": "user_abc123",
  "items": [
    {
      "id": "sem_02k8...",
      "type": "semantic",
      "content": "User studies computer science",
      "confidence": 0.95,
      "importance": 8.0,
      "timestamp": "2026-04-02T09:15:00Z",
      "session_id": "sess_abc",
      "source_turn": 5,
      "category": "education",
      "verification_count": 2,
      "last_verified": "2026-05-10T00:00:00Z",
      "access_count": 7,
      "last_accessed": "2026-06-19T08:00:00Z",
      "created_at": "2026-04-02T09:15:00Z",
      "updated_at": "2026-05-10T00:00:00Z"
    }
  ]
}
```

### preference.json

```json
{
  "version": 1,
  "user_id": "user_abc123",
  "items": [
    {
      "id": "pref_03m9...",
      "type": "preference",
      "content": "User prefers local AI models over cloud",
      "confidence": 0.88,
      "importance": 7.0,
      "strength": 0.8,
      "timestamp": "2026-04-05T16:45:00Z",
      "session_id": "sess_def",
      "source_turn": 8,
      "category": "model_preference",
      "polarity": "positive",
      "domain": "ai_models",
      "access_count": 5,
      "last_accessed": "2026-06-17T12:00:00Z",
      "created_at": "2026-04-05T16:45:00Z",
      "updated_at": "2026-06-17T12:00:00Z"
    }
  ]
}
```

### Common Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID v7 (time-ordered) |
| `type` | enum | `episodic`, `semantic`, `preference` |
| `content` | string | The memory text (1 sentence, concrete) |
| `confidence` | float | 0.0–1.0, how sure we are this is correct |
| `importance` | float | 1.0–10.0, how significant this memory is |
| `timestamp` | ISO 8601 | When the triggering event occurred |
| `session_id` | string | Which session produced this |
| `source_turn` | int | Turn number within session |
| `access_count` | int | How many times retrieved |
| `last_accessed` | ISO 8601 | Last retrieval timestamp |
| `created_at` | ISO 8601 | When first stored |
| `updated_at` | ISO 8601 | When last modified |

---

## 4. Data Flow Diagrams

### 4A. Main Request Flow (Read Path)

```
User Message
    │
    ▼
Orchestrator
    │
    ├──► Intent Classification
    │
    ├──► Working Memory Buffer (current session turns)
    │
    ├──► Retrieval Pipeline
    │       │
    │       ├──► Query Rewriting (enhance query with context)
    │       │
    │       ├──► Episodic Store.search(query, top_k)
    │       ├──► Semantic Store.search(query, top_k)
    │       ├──► Preference Store.search(query, top_k)
    │       │
    │       └──► Fusion & Ranking
    │               ├── Confidence-weighted scoring
    │               ├── Recency boost
    │               ├── Relevance to query (embedding cosine + keyword)
    │               └── Top-N selection (default: 8)
    │
    ├──► Context Assembly
    │       Working Buffer + Retrieved Memories → Prompt Context
    │
    ├──► LLM Generation
    │
    └──► Post-Response: Extraction Pipeline (async)
            │
            ├──► Extract candidates from (user_msg + assistant_msg)
            ├──► Classify into episodic / semantic / preference
            ├──► Assign confidence score
            ├──► Run duplicate detection against existing stores
            ├──► Merge or insert
            └──► Persist to JSON
```

### 4B. Extraction Pipeline (Write Path)

```
User: "I built TabMind last month, it was a cool project"
Assistant: "That's awesome! What tech stack did you use?"

    │
    ▼
Extraction Pipeline (async, after response sent)
    │
    ├── 1. Extract Candidate Items
    │      For each (user_msg, assistant_msg) pair:
    │      - LLM extracts structured memories
    │      - Returns: {"episodic": [...], "semantic": [...], "preference": [...]}
    │
    ├── 2. Confidence Scoring
    │      Each item gets a confidence score:
    │      - Explicit statement: base 0.9
    │      - Implicit inference: base 0.6
    │      - Vague reference: base 0.3
    │      - Adjustments: repetition (+0.1), contradiction (-0.3)
    │
    ├── 3. Classify & Tag
    │      - Assign type (episodic / semantic / preference)
    │      - Extract contextual metadata (verb, object, category)
    │      - Assign importance
    │
    ├── 4. Duplicate Detection
    │      For each candidate:
    │      - Check existing stores for semantic near-match
    │      - Lexical overlap (Jaccard > 0.6) → candidate duplicate
    │      - Embedding cosine similarity > 0.85 → candidate duplicate
    │
    ├── 5. Merge or Insert
    │      If duplicate found:
    │      - Merge confidence: max(existing.confidence, new.confidence)
    │      - Update content if newer is more detailed
    │      - Increment verification_count / strength
    │      - Touch updated_at
    │      If new:
    │      - Assign UUID, set timestamps
    │      - Insert into appropriate store
    │
    └── 6. Persist
           - Write to JSON file via StorageBackend
           - Async, non-blocking
```

### 4C. Update Pipeline (Maintenance)

```
Triggered by:
  A. After each extraction (merge step)
  B. Scheduled maintenance (every N hours)
  C. On explicit user correction ("no, that's wrong")

    │
    ▼
Update Pipeline
    │
    ├── 1. Confidence Decay
    │      For all items:
    │      - confidence *= 0.99^(days_since_last_accessed)
    │      - importance *= 0.97^(days_since_created)
    │      - Items below threshold (confidence < 0.2) → archive
    │
    ├── 2. Reinforcement
    │      For items accessed recently:
    │      - importance += 0.5 (capped at 10.0)
    │      - confidence = min(1.0, confidence + 0.02)
    │
    ├── 3. Conflict Resolution
    │      Detect contradictory pairs:
    │      - Same category, opposite polarity
    │      - "User prefers X" vs "User prefers not X"
    │      - Keep higher confidence, flag for review
    │
    ├── 4. Consolidation
    │      Merge highly overlapping items:
    │      - content overlap > 80% → merge into one
    │      - Keep longest content, highest confidence
    │
    └── 5. Archival
         - Items below decay threshold
         - Items flagged as invalid by user correction
         - Moved to archived section (not deleted, just hidden)
```

---

## 5. Memory Retrieval Algorithm

```
FUNCTION retrieve_memories(query, user_id, top_k=8):

    // Phase 1: Query enhancement
    enhanced_query = query
    if working_buffer.has_recent_context():
        enhanced_query = working_buffer.last_topic() + " " + query

    // Phase 2: Multi-store parallel search
    episodic_results = episodic_store.search(
        query=enhanced_query,
        user_id=user_id,
        top_k=top_k * 2,
        min_confidence=CONFIDENCE_FLOOR  // 0.3
    )

    semantic_results = semantic_store.search(
        query=enhanced_query,
        user_id=user_id,
        top_k=top_k * 2,
        min_confidence=CONFIDENCE_FLOOR
    )

    preference_results = preference_store.search(
        query=enhanced_query,
        user_id=user_id,
        top_k=top_k,
        min_confidence=CONFIDENCE_FLOOR
    )

    // Phase 3: Merge candidates
    candidates = episodic_results + semantic_results + preference_results

    // Phase 4: Score each candidate
    FOR each item in candidates:

        // 4a. Semantic relevance (embedding cosine similarity)
        semantic_score = cosine_similarity(
            embed(enhanced_query),
            embed(item.content)
        )

        // 4b. Confidence score
        confidence_score = item.confidence

        // 4c. Recency score (exponential decay, half-life = 30 days)
        days_old = (now - item.timestamp).days
        recency_score = 0.5 ^ (days_old / 30)

        // 4d. Importance score (normalized to 0-1)
        importance_score = item.importance / 10.0

        // 4e. Access frequency boost
        access_score = min(1.0, item.access_count / 10)

        // 4f. Combined score
        item.score = (
            semantic_score     * 0.35 +
            confidence_score   * 0.25 +
            recency_score      * 0.15 +
            importance_score   * 0.15 +
            access_score       * 0.10
        )

    // Phase 5: Rank and filter
    ranked = sort_descending(candidates, by=score)
    ranked = filter(ranked, where=score > RELEVANCE_THRESHOLD)  // 0.15
    top = first(ranked, top_k)

    // Phase 6: Dedup final list
    return dedup_by_content(top)
```

### Scoring Weights Rationale

| Weight | Factor | Rationale |
|--------|--------|-----------|
| 0.35 | Semantic relevance | Highest weight: the memory must be about what the user asked |
| 0.25 | Confidence | Second: we should only surface things we're sure about |
| 0.15 | Recency | Moderate: recent matters but old facts can still be important |
| 0.15 | Importance | Moderate: some memories are inherently more significant |
| 0.10 | Access frequency | Lowest: frequently accessed memories are likely useful |

---

## 6. Memory Update Algorithm

### Extraction Trigger

```
FUNCTION extract_memories(user_msg, assistant_msg, session_context):

    // 1. Check if extraction is warranted
    IF is_greeting(user_msg) OR is_short(user_msg, min_words=4):
        RETURN  // Skip extraction for trivial exchanges

    // 2. Call LLM for structured extraction
    extraction_result = llm.extract_memories(
        user_message=user_msg,
        assistant_response=assistant_msg,
        instruction=EXTRACTION_PROMPT
    )
    // Returns: {episodic: [str], semantic: [str], preference: [str]}

    // 3. Process each extracted item
    FOR each (type, content_list) in extraction_result:
        FOR each content in content_list:

            // 3a. Compute confidence
            confidence = compute_confidence(content, user_msg, type)

            // 3b. Compute importance
            importance = compute_importance(content, type)

            // 3c. Skip low-confidence items
            IF confidence < MIN_CONFIDENCE:  // 0.3
                CONTINUE

            // 3d. Build memory item
            item = MemoryItem(
                id = generate_uuid_v7(),
                type = type,
                content = content,
                confidence = confidence,
                importance = importance,
                timestamp = now(),
                session_id = session_context.session_id,
                source_turn = session_context.turn_number,
            )

            // 3e. Duplicate detection
            existing = find_duplicate(item)
            IF existing:
                merged = merge_items(existing, item)
                store.update(existing.id, merged)
            ELSE:
                store.insert(item)
```

### Confidence Scoring

```
FUNCTION compute_confidence(content, user_msg, type):

    score = 0.0

    // Signal 1: Directness of statement
    IF user_msg contains "I am", "I study", "I work", "my name":
        score += 0.5    // Explicit self-disclosure
    ELIF user_msg contains "I like", "I prefer", "I love", "I hate":
        score += 0.4    // Preference disclosure
    ELIF user_msg contains "I think", "I feel", "maybe", "perhaps":
        score += 0.2    // Opinion/uncertainty
    ELSE:
        score += 0.3    // Inferred from conversation

    // Signal 2: Specificity
    IF contains_proper_noun(content):
        score += 0.2
    IF contains_number_or_date(content):
        score += 0.15
    IF word_count(content) >= 8:
        score += 0.1

    // Signal 3: Contradiction check
    contradictory = find_contradicting_memories(content)
    IF contradictory:
        score -= 0.3

    // Signal 4: Repetition bonus
    similar = find_similar_memories(content, threshold=0.7)
    IF similar:
        score += min(0.2, len(similar) * 0.05)

    return clamp(score, 0.0, 1.0)
```

### Duplicate Detection

```
FUNCTION find_duplicate(candidate):

    // Pass 1: Exact content match (fast path)
    exact = store.find_exact(candidate.content)
    IF exact:
        RETURN exact

    // Pass 2: Lexical overlap (Jaccard similarity)
    candidate_tokens = tokenize(candidate.content)
    FOR each existing in store:
        existing_tokens = tokenize(existing.content)
        intersection = |candidate_tokens ∩ existing_tokens|
        union = |candidate_tokens ∪ existing_tokens|
        jaccard = intersection / union
        IF jaccard > JACCARD_THRESHOLD (0.6):
            RETURN existing

    // Pass 3: Embedding similarity
    candidate_vec = embed(candidate.content)
    FOR each existing in store:
        existing_vec = embed(existing.content)
        cosine = cosine_similarity(candidate_vec, existing_vec)
        IF cosine > EMBEDDING_THRESHOLD (0.85):
            RETURN existing

    RETURN null
```

### Merge on Conflict

```
FUNCTION merge_items(existing, candidate):

    // Content: prefer more specific
    merged_content = existing.content
    IF word_count(candidate.content) > word_count(existing.content) * 1.3:
        merged_content = candidate.content

    // Confidence: take max
    merged_confidence = max(existing.confidence, candidate.confidence)

    // Importance: weighted combination for reinforcement
    merged_importance = min(10.0, existing.importance + 0.5)

    // Verification: increment
    merged_verification = existing.verification_count + 1

    // Timestamps
    merged_updated = now()
    merged_timestamp = min(existing.timestamp, candidate.timestamp)
    // Keep original creation time

    RETURN MemoryItem(
        id = existing.id,  // Preserve original ID
        content = merged_content,
        confidence = merged_confidence,
        importance = merged_importance,
        verification_count = merged_verification,
        timestamp = merged_timestamp,
        updated_at = merged_updated,
        // Preserve other fields from existing
    )
```

---

## 7. Integration with Existing System

### Entry Points

The new memory system replaces the current `chat_manager_v3.py` memory layer:

```
Current:                        New:
chat_manager_v3.py              orchestrator.py
├── MemoryController ──►        │
├── MemoryRetriever  ──►        ├── MemoryV2Retriever
├── MemoryUpdater    ──►        ├── MemoryV2Extractor
├── ContextAssembler ──►        └── ContextAssembler (reuse)
└── LongTermMemory              (deprecated)
```

### Migration Path

1. Phase 1: `memory_v2/` runs alongside `memory/` in parallel
2. Phase 2: Toggle via feature flag `MEMORY_V2_ENABLED=true`
3. Phase 3: Deprecate old modules, remove `memory/` directory

### Working Memory Buffer

The working buffer is NOT JSON-persisted. It lives in-memory in `working/buffer.py`:

```
WorkingBuffer:
  - per-session sliding window (max 50 turns)
  - LRU eviction when full
  - Provides:
      .append(role, content)
      .get_context() → recent turns as formatted string
      .last_topic()  → summarized last topic
      .clear()       → on session end
```

---

## 8. Key Design Decisions

### Why JSON First, SQLite Later

- **JSON**: Zero dependencies, trivially debuggable (open in any editor), no schema migrations during prototyping
- **SQLite**: For production: indexed queries, atomic writes, concurrent access, smaller memory footprint
- **Migration**: The `StorageBackend` abstraction means swapping storage is a one-file change

### Why Four Layers Instead of Three

The current 3-layer model (short/medium/long-term) is about *time scale*. The new 4-layer model is about *information type*:

| Model | Organization | Query Pattern |
|-------|-------------|---------------|
| Old (3-layer) | "how recent?" | Single sequence |
| New (4-layer) | "what kind?" | Type-specific retrieval |

This means:
- Episodic memory answers "what happened?"
- Semantic memory answers "what is true?"
- Preference memory answers "what do they like?"
- Working memory answers "what were we just saying?"

Each type benefits from different retrieval strategies (temporal for episodic, factual for semantic, categorical for preference).

### Why Confidence Scoring

Without confidence, the system cannot distinguish between:
- "User built TabMind" (explicitly stated, high confidence)
- "User might be interested in AI" (inferred, low confidence)

Confidence enables:
- Graceful degradation (low confidence = don't surface unless highly relevant)
- Conflict resolution (higher confidence wins)
- Decay (unreinforced low-confidence items fade first)
