# Kuro AI — Memory Extractor Design

## Purpose

The Memory Extractor is the gatekeeper of the memory system. Given a raw conversation turn (user message + assistant response), it decides what is worth remembering, assigns a type and confidence score, and produces a structured memory item ready for storage.

---

## 1. Extraction Flow

```
User Message + Assistant Response
         │
         ▼
┌─────────────────────────────┐
│   Stage 1: Filter           │  ← Skip trivial turns
│   - Greeting check          │
│   - Length check            │
│   - Temporality check       │
│   - Self-referential check  │
└──────────┬──────────────────┘
           │ (passes filter)
           ▼
┌─────────────────────────────┐
│   Stage 2: Extract          │  ← LLM call
│   - Structured extraction   │
│   - Per-category output     │
└──────────┬──────────────────┘
           │ (raw candidates)
           ▼
┌─────────────────────────────┐
│   Stage 3: Score            │  ← Rule-based post-processing
│   - Confidence per item     │
│   - Importance per item     │
│   - Rejection or accept     │
└──────────┬──────────────────┘
           │ (scored items)
           ▼
┌─────────────────────────────┐
│   Stage 4: Dedup            │  ← Check existing stores
│   - Exact match             │
│   - Lexical overlap         │
│   - Semantic similarity     │
└──────────┬──────────────────┘
           │ (unique items)
           ▼
        STORE
```

---

## 2. Stage 1: Pre-Filter (No LLM)

Before making an LLM call, rule out conversations that cannot possibly contain useful memories.

### Filter Rules

| Rule | Condition | Action |
|------|-----------|--------|
| **Greeting** | User message ≤ 6 words AND contains greeting keywords (hi, hello, hey, sup, yo, good morning, good evening, howdy, what's up, how are you) | Skip |
| **Too short** | User message ≤ 3 words and no named entities | Skip |
| **Only acknowledgment** | User message is "ok", "thanks", "got it", "cool", "nice" (exact or with minor variation) | Skip |
| **Only questions about Kuro** | "who are you", "what can you do", "how do you work", "are you AI" | Skip |
| **Only system commands** | "clear", "reset", "undo", "stop", "help" | Skip |
| **Temporary micro-planning** | "remind me to", "I'll do it later", "let me check", "I'll get back to you" | Skip |
| **Contains self-disclosure signal** | "I am", "I'm", "I work", "I study", "I like", "I built", "I created", "my name", "I prefer", "I use", "I live", "my job" | Pass to Stage 2 |
| **Contains past-tense event** | "I built", "I went", "I tried", "I started", "I made", "I switched" | Pass to Stage 2 |
| **Contains preference signal** | "I like", "I prefer", "I love", "I hate", "I dislike", "my favorite" | Pass to Stage 2 |
| **Contains future commitment** | "I'm going to", "I plan to", "I will", "I want to" but with concrete noun (project, degree, move, build, study, start) | Pass to Stage 2 |

### Cost-Benefit Logic

LLM extraction calls are expensive (~500ms-1000ms latency, token cost). The pre-filter ensures we only call the LLM when there is a reasonable chance of finding extractable memories. Estimated filter pass rate: 20-30% of all conversation turns.

---

## 3. Stage 2: Extraction (LLM)

### Extraction Prompt Architecture

The prompt instructs the LLM to produce structured memory candidates. Key design constraints:

1. **Three output arrays**: `episodic`, `semantic`, `preference` — empty if nothing found
2. **One sentence per item**: concrete, context-independent, maximally informative
3. **Normalize references**: Change "I", "me", "my" to "User" so memories read in third person
4. **No explanations**: just emit JSON arrays

### Extraction Prompt (Conceptual)

```
You are a memory extraction system. Given a conversation turn, identify information
worth remembering long-term about the user.

CATEGORIES:
- episodic: Events, experiences, actions the user has taken. Things that happened.
  Examples: "User built a project called TabMind", "User switched from cloud to local models"
- semantic: Facts about the user that are generally true. Identity, skills, background.
  Examples: "User studies computer science", "User lives in New York"
- preference: User's likes, dislikes, preferences, habits.
  Examples: "User prefers local AI models", "User dislikes proprietary software"

RULES:
- Write each memory as a single sentence starting with "User"
- Keep facts concrete and specific. Avoid vague statements.
- Skip information that is likely temporary (mood, fleeting thoughts, today's tasks)
- Skip greetings, thanks, pleasantries, and filler
- Skip questions the user asks Kuro (unless they reveal something about the user)
- If nothing is worth extracting, return empty arrays

CONVERSATION:
User: {user_message}
Assistant: {assistant_response}

OUTPUT (JSON only):
{
  "episodic": ["..."],
  "semantic": ["..."],
  "preference": ["..."]
}
```

### What to Extract — Decision Matrix

| User says... | Extracts? | Category | Why |
|---|---|---|---|
| "I built TabMind" | Yes | Episodic | Concrete past event |
| "I study CS" | Yes | Semantic | Enduring fact |
| "I like local models" | Yes | Preference | Explicit preference |
| "I'm tired today" | No | — | Temporary state |
| "I need milk" | No | — | Fleeting task |
| "I have a CS degree" | Yes | Semantic | Enduring credential |
| "I was thinking about AI" | Weak | Episodic (if elaborated) | Vague thought |
| "I just switched to Linux" | Yes | Episodic | Concrete event |
| "Thanks, that helped" | No | — | Filler |
| "My name is Alex" | Yes | Semantic | Core identity fact |
| "I work at Google" | Yes | Semantic | Job fact |
| "I hate Mondays" | No | — | General complaint, not specific |
| "I hate using Windows" | Yes | Preference | Specific stated preference |
| "I moved to SF in 2023" | Yes | Episodic | Concrete temporal event |
| "Can you write a poem?" | No | — | Task request, no self-disclosure |
| "I prefer dark mode" | Yes | Preference | Explicit UI preference |

---

## 4. Stage 3: Confidence Scoring (Rule-Based)

After the LLM returns candidates, each item is scored by a deterministic rule system. The LLM does NOT assign confidence — that would be expensive and inconsistent. Instead, we score based on signals in the original user message.

### Confidence Formula

```
confidence = base_score + directness_bonus + specificity_bonus - vagueness_penalty + repetition_bonus

Result clamped to [0.0, 1.0]
```

### Base Score by Category

| Category | Base | Rationale |
|----------|------|-----------|
| Episodic | 0.60 | Events can be misremembered or exaggerated |
| Semantic | 0.65 | Facts are generally stable but can be partial truths |
| Preference | 0.55 | Preferences can change; user may not be fully aware of own preferences |

### Signal Detection

#### Directness Bonus (+0.0 to +0.35)

| Signal | Bonus | Detection |
|--------|-------|-----------|
| Explicit "I am / I'm / I study / I work / my name" | +0.35 | Regex on user message |
| Explicit "I like / I prefer / I love / I hate" | +0.30 | Regex on user message |
| Explicit "I built / I created / I made / I started" | +0.30 | Regex on user message |
| Explicit "I have / I've got / I own" | +0.25 | Regex on user message |
| Implicit but clear context | +0.15 | Inferred from conversation flow |
| Mentioned in passing | +0.05 | Extracted from offhand comment |

#### Specificity Bonus (+0.0 to +0.25)

| Signal | Bonus | Detection |
|--------|-------|-----------|
| Contains proper noun (capitalized word not at start) | +0.10 | Regex `[A-Z][a-z]+` excluding first word |
| Contains number (year, age, count) | +0.08 | Regex `\b\d+\b` |
| Contains date or month | +0.07 | Regex month names or year patterns |
| Contains specific domain term | +0.05 | "computer science", "machine learning", "React", etc. |
| Item length ≥ 10 words | +0.05 | More detail = more specific |

#### Vagueness Penalty (-0.0 to -0.30)

| Signal | Penalty | Detection |
|--------|---------|-----------|
| Contains "maybe", "perhaps", "kind of", "sort of" | -0.15 | Regex hedging language |
| Contains "I think", "I feel", "I believe" | -0.10 | Opinion frame |
| Contains "someone", "something", "somewhere" | -0.10 | Indefinite reference |
| Vague time: "recently", "lately", "sometime" (without anchor) | -0.08 | Temporal vagueness |
| Memory item length < 5 words | -0.15 | Too short to be specific |

#### Repetition Bonus (+0.0 to +0.15)

If the user has mentioned the same fact across multiple turns, confidence increases.

| Signal | Bonus |
|--------|-------|
| First mention | +0.00 |
| Second mention (same session) | +0.08 |
| Third+ mention (any session) | +0.15 |

Detection: query existing stores for near-match content before insertion.

#### Example Confidence Calculations

**Example A: High confidence**
```
User: "I built a project called TabMind last year using Python and FastAPI"

Signals:
- Base (episodic)        0.60
- Directness "I built"  +0.30
- Proper noun "TabMind"  +0.10
- Proper noun "FastAPI"  +0.10
- Number "last year"     +0.00 (implicit time, no explicit number)
- Length ≥ 10 words      +0.05
- No hedging             +0.00
- First mention          +0.00
Total: 1.15 → clamped to 1.00
Confidence: 1.00 (very high)
```

**Example B: Medium confidence**
```
User: "I think I prefer local models over cloud"

Signals:
- Base (preference)      0.55
- Directness "I prefer" +0.30
- No proper nouns        +0.00
- No numbers             +0.00
- "I think" hedge       -0.10
- Length ≥ 10 words?     No (8 words) +0.00
Total: 0.75
Confidence: 0.75 (moderate)
```

**Example C: Low confidence (should be rejected)**
```
User: "I kinda like coding I guess"

Signals:
- Base (preference)      0.55
- "I like"              +0.30
- No proper nouns        +0.00
- "kinda" hedge         -0.15
- "I guess" hedge       -0.15
- Length < 5 words       -0.15
Total: 0.40
Confidence: 0.40 (low — reject, below 0.50 threshold)
```

### Acceptance Threshold

| Confidence Range | Action |
|-----------------|--------|
| 0.00 – 0.49 | **Reject**: too uncertain, do not store |
| 0.50 – 0.69 | **Store with low priority**: high decay rate, low retrieval weight |
| 0.70 – 0.89 | **Store normally**: standard retrieval weight |
| 0.90 – 1.00 | **Store with high priority**: low decay, high retrieval weight |

---

## 5. Stage 4: Deduplication Strategy

Before inserting a new memory item, check existing stores to avoid duplicates.

### Three-Pass Dedup

#### Pass 1: Exact Match (O(1) via hash index)
```
Normalize content: lowercase, strip punctuation, collapse whitespace
Hash normalized content
If hash exists in index → EXACT DUPLICATE
  Action: Merge confidence (max of old and new),
          increment verification_count,
          update last_verified timestamp
          REJECT insertion, UPDATE existing
```

#### Pass 2: Lexical Overlap (Jaccard Similarity) — O(n)
```
Tokenize: split into words, lowercase, remove stopwords
Compute Jaccard similarity:
  intersection = |tokens1 ∩ tokens2|
  union = |tokens1 ∪ tokens2|
  jaccard = intersection / union

If jaccard > 0.65 → LEXICAL DUPLICATE
  Action: Merge (keep longer content, higher confidence),
          increment verification_count
          REJECT insertion, UPDATE existing
```

#### Pass 3: Semantic Similarity (Embedding Cosine) — O(n)
```
Compute embedding vector for new content (384-dim from Gemini)
For each existing item in same memory type:
  cosine_sim = dot_product(new_vec, existing_vec) / (|new_vec| * |existing_vec|)
  If cosine_sim > 0.82 → SEMANTIC DUPLICATE
    Action: Merge (keep more specific content, higher confidence),
            increment verification_count
            REJECT insertion, UPDATE existing
```

### What "Merge" Means

When a duplicate is found, the existing item is updated, not replaced:

```
merged = {
    "content": longer_of(old.content, new.content),
    "confidence": max(old.confidence, new.confidence),
    "importance": min(10.0, old.importance + 0.5),  # reinforcement
    "verification_count": old.verification_count + 1,
    "last_verified": now(),
    "updated_at": now()
    # Preserve original created_at, id
}
```

### Unique Dedup: Same Fact, Different Type

If the same fact is extracted as both `episodic` AND `semantic`:

| Candidate | Existing | Resolution |
|-----------|----------|------------|
| "User built TabMind" (episodic) | "User built TabMind" (semantic) | Keep both. Episodic captures the event, semantic captures the enduring fact. Different retrieval purposes. |
| "User prefers local AI" (preference) | "User switched to local AI" (episodic) | Keep both. One is preference, one is the event that triggered it. Cross-reference via session_id. |

### Cross-Type Dedup Exception

Episodic and Semantic memories CAN overlap in content because they serve different retrieval needs:
- Episodic: retrieved when asking "what happened?"
- Semantic: retrieved when asking "what is true about the user?"

However, if an episodic and semantic item have IDENTICAL content (>0.95 cosine), the semantic version replaces the episodic (semantic is more stable).

---

## 6. Edge Cases

### Edge Case 1: User corrects a previous statement
```
User: "Actually, I don't study CS anymore. I switched to Data Science."
```
**Extraction**: `"User switched from computer science to data science"` (episodic, high confidence)
**Dedup**: Detects conflict with existing "User studies computer science" (semantic).
**Resolution**: Original semantic memory gets `confidence *= 0.5` (decayed by contradiction). New episodic memory stored with high confidence. A `contradicts` field links the two items.

### Edge Case 2: User talks about someone else
```
User: "My friend Sarah built a really cool app."
```
**Extraction**: `"User's friend Sarah built a cool app"` (episodic, medium confidence)
**Filter**: Still valuable — it tells us the user's social context. But confidence is lower because it's second-hand.

### Edge Case 3: User expresses hypothetical
```
User: "If I had more time, I'd learn Rust."
```
**Extraction**: Reject. Hypotheticals are not actual events or confirmed preferences. Confidence would be ~0.35 (below threshold).

### Edge Case 4: Multi-fact turn
```
User: "I'm a CS student at MIT, and last summer I built a compiler in Rust. I prefer functional programming."
```
**Extraction**:
1. Semantic: "User studies computer science at MIT" (confidence: 1.00)
2. Episodic: "User built a compiler in Rust last summer" (confidence: 1.00)
3. Preference: "User prefers functional programming" (confidence: 0.85)
All three stored — they are independent facts.

### Edge Case 5: User contradicts mid-conversation
```
Turn 5: "I love VS Code"
Turn 12: "Actually, I switched to Neovim. VS Code is too heavy."
```
**Turn 5 extraction**: `"User loves VS Code"` (preference, confidence: 0.80)
**Turn 12 extraction**: `"User switched from VS Code to Neovim"` (episodic, confidence: 0.95)
**Resolution**: The preference item should be updated to reflect the change. The system detects the subject overlap ("VS Code") and decays the old preference. A new preference "User prefers Neovim" is NOT inferred unless explicitly stated.

### Edge Case 6: User asks a question about themselves
```
User: "Do you remember what I studied?"
```
**Extraction**: Skip — this is a query, not a disclosure. No new information.
**Retrieval**: Triggered by the recall signal in the main pipeline, but the extractor should reject this.

### Edge Case 7: Single very long turn with mixed content
```
User: "Hey, how are you? Good. So I've been working on this project called Kuro for a while now.
      It's an AI assistant. I'm using FastAPI for the backend and React for the frontend.
      By the way, do you know any good resources for learning about vector databases?"
```
**Extraction**:
1. Episodic: "User is working on a project called Kuro" (confidence: 0.95)
2. Semantic: "User builds AI assistants" (confidence: 0.75 — inferred, lower)
3. Semantic: "User works with FastAPI and React" (confidence: 0.90)
4. Preference: (nothing — question about vector databases is not a stated preference)

### Edge Case 8: Non-English content
```
User: "Je suis développeur Python à Paris"
```
**Extraction**: Treat the same — the LLM should extract in English (normalized).
"User is a Python developer in Paris" (semantic, confidence: 0.90)
The LLM translates during extraction.

### Edge Case 9: Self-deprecating or negative statements
```
User: "I'm bad at math. I could never be a data scientist."
```
**Extraction**: 
1. Semantic: "User considers themselves weak at mathematics" (confidence: 0.70)
2. Preference: "User believes data science is not for them" (confidence: 0.55 — lower, could be situational)
**Warning**: These may not be objectively true but reflect the user's self-perception. The system stores them as stated, with the confidence reflecting that it's self-reported. If the user later contradicts ("actually I'm good at math now"), conflict resolution handles it.

### Edge Case 10: Empty or malformed LLM output
```
LLM returns: {"episodic": [], "semantic": [], "preference": []}
```
**Action**: Nothing to store. Return early.

```
LLM returns unparsable: "I couldn't find any memories here."
```
**Action**: Treat as empty extraction. Log the parsing failure but do not crash. Return empty result.

---

## 7. Importance Scoring

In addition to confidence, each memory gets an **importance** score (1.0–10.0) that determines retrieval weight and decay rate.

### Importance Rules

| Signal | Adjustment |
|--------|------------|
| Core identity ("name", "work", "study", "live") | +3.0 |
| Long-term project or skill | +2.0 |
| Explicit preference | +1.5 |
| Contains proper noun | +1.0 |
| Contains number/date | +0.5 |
| Hedged or uncertain | -1.0 |
| Third-party information | -1.5 |
| Base | 5.0 |

Clamped to [1.0, 10.0].

### Importance vs Confidence

| | Confidence | Importance |
|---|---|---|
| Measures | How sure we are it's true | How significant it is |
| Used for | Whether to store, merge decisions | Retrieval ranking, decay rate |
| Changes over time | Can decrease with contradiction | Can increase with reinforcement |
| Example | "User might like Python" = 0.55 | "User is a Python developer" = 8.0 |

---

## 8. Complete Item Example

```
Input:
  User: "I just finished migrating my entire infrastructure from AWS to GCP.
         I spent three months on it. Definitely prefer GCP's UI."

Output items:

1. {
    "memory_type": "episodic",
    "content": "User migrated infrastructure from AWS to GCP over three months",
    "confidence": 0.98,
    "importance": 8.5,
    "reasoning": "Explicit past event 'just finished migrating', concrete platforms 'AWS' and 'GCP', temporal anchor 'three months'. High directness and specificity."
  }

2. {
    "memory_type": "semantic",
    "content": "User manages cloud infrastructure",
    "confidence": 0.82,
    "importance": 7.0,
    "reasoning": "Inferred from the event — if they migrated entire infrastructure, they likely work with cloud infra. Lower confidence because inferred rather than stated."
  }

3. {
    "memory_type": "preference",
    "content": "User prefers GCP over AWS",
    "confidence": 0.90,
    "importance": 7.5,
    "reasoning": "Explicit preference statement 'prefer GCP's UI'. High directness. Slight deduction for being UI-specific rather than platform-wide."
  }
```

---

## 9. Self-Diagnostics

The extractor should expose a debug endpoint that answers:

| Question | Insight |
|----------|---------|
| How many turns were filtered? | Pre-filter effectiveness |
| What was the average confidence of extracted items? | Extraction quality |
| How many items were rejected by confidence threshold? | Over-extraction rate |
| How many duplicates were found? | Memory saturation |
| What is the avg LLM response time for extraction? | Cost monitoring |
