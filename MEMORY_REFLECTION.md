# Kuro AI — Reflection Engine

## Purpose

The other memory layers store observations (episodic), facts (semantic), preferences, behavior patterns (procedural), and recent context (working). The Reflection Engine is the meta-layer — it reads across these stores, detects latent themes, and generates insights that are greater than the sum of individual memories.

An insight is not a fact. It is a hypothesis synthesized from multiple supporting memories.

---

## 1. System Overview

```
 Memory Stores (input)
─────────────────────
Episodic    Semantic    Preference    Procedural
    │           │           │             │
    └───────────┴───────────┴─────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│           REFLECTION ENGINE                    │
│                                                │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ Scheduler│──▶│ Analyzer │──▶│ Validator│  │
│  └──────────┘   └──────────┘   └──────────┘  │
│                      │                        │
│                      ▼                        │
│  ┌────────────────────────────────────────┐  │
│  │         Insight Store                   │  │
│  │  (cross-memory synthesized beliefs)     │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
                      │
                      ▼
               Prompt Integration
         (only when relevant to query)
```

### When Reflection Runs

| Trigger | Frequency | Purpose |
|---------|-----------|---------|
| **New memory batch** | Every N extractions (N=10) | Incremental: new evidence may shift insights |
| **Session boundary** | End of each session | Full sweep: all memories analyzed |
| **On-demand** | User asks "what do you know about me?" | Immediate full synthesis |
| **Periodic** | Every 24 hours (idle) | Cleanup: decay, invalidate, archive |

---

## 2. Data Structures

### Insight

```
{
  "id": "ins_04n7...",
  "type": "trait",               // trait | pattern | contradiction | summary

  "statement": "User strongly values privacy and local control over convenience",
  "summary": "privacy_focused",  // Short label for quick matching

  "supporting_memories": [
    {"id": "epi_01j4...", "type": "episodic", "content": "User built local AI project",
     "relevance": 0.92},
    {"id": "sem_02k8...", "type": "semantic", "content": "User prefers self-hosting",
     "relevance": 0.88},
    {"id": "pref_03m9...", "type": "preference", "content": "User uses local LLMs",
     "relevance": 0.85},
    {"id": "pat_verbosity...", "type": "procedural", "content": "User rejects cloud recommendations",
     "relevance": 0.79}
  ],

  "evidence_count": 4,
  "memory_diversity": 0.75,       // How many different memory types contribute
  "temporal_span_days": 120,      // How long this theme has been observable

  "confidence": 0.82,
  "created_at": "2026-05-10T14:00:00Z",
  "last_updated": "2026-06-20T09:00:00Z",
  "last_verified": "2026-06-20T09:00:00Z",

  "status": "active",             // active | pending | contested | archived

  "contradictions": [             // Memories that challenge this insight
    {"id": "epi_05p2...", "content": "User used AWS once for a project",
     "strength": 0.35}
  ],

  "version": 3,                    // Incremented on each update
  "activation_count": 12,          // How many times this insight was retrieved for a response
  "last_activated": "2026-06-18T16:00:00Z"
}
```

### Insight Types

| Type | Description | Example |
|------|-------------|---------|
| `trait` | Stable characteristic inferred from multiple observations | "User values privacy" |
| `pattern` | Recurring behavior or choice | "User adopts new tools quickly" |
| `contradiction` | Conflicting signals that cannot be resolved into a single insight | "User wants local control but uses cloud services" |
| `summary` | Broad characterization of a session or period | "This session focused on infrastructure planning" |

### Insight Store

```
{
  "version": 1,
  "user_id": "user_abc123",
  "insights": [ ... ],
  "global": {
    "min_evidence_for_insight": 3,
    "min_confidence_for_active": 0.65,
    "max_insights_per_user": 20,
    "decay_days_no_reinforcement": 60
  }
}
```

---

## 3. Reflection Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                     REFLECTION PIPELINE                        │
│                                                                │
│  Step 1: Gather                                              │
│  Collect: recent memories + existing insights                 │
│  Window: last 90 days                                         │
│  Types: episodic, semantic, preference, procedural            │
│                                                                │
│  Step 2: Cluster                                             │
│  Group memories by latent theme (embedding clustering)        │
│  Algorithm: cosine similarity > 0.65 → same cluster           │
│  Min cluster size: 3 memories                                 │
│                                                                │
│  Step 3: Synthesize                                          │
│  For each cluster:                                            │
│    LLM analyzes supporting memories                           │
│    Generates candidate insight statement                      │
│    Identifies type (trait/pattern/contradiction/summary)      │
│                                                                │
│  Step 4: Score                                               │
│  Confidence = coherence × coverage × specificity × stability  │
│  (See Section 4)                                              │
│                                                                │
│  Step 5: Validate                                            │
│  Check against existing insights for:                         │
│  - Duplicate (merge or skip)                                  │
│  - Contradiction (flag, adjust confidence)                    │
│  - Hallucination (reject if insufficient evidence)            │
│                                                                │
│  Step 6: Store                                               │
│  Insert new or update existing                                │
│  Bump version number                                          │
│  Update timestamps                                            │
└──────────────────────────────────────────────────────────────┘
```

### Step 1: Gather

```
INPUT:
  - All memories from last 90 days (confidence ≥ 0.50)
  - All active insights
  - Recent procedural rules

OUTPUT:
  - Flat list of memory items with their embeddings
  - Existing insight statements

FILTERS:
  - Exclude greetings and trivial observations
  - Exclude memories with confidence < 0.50
  - Deduplicate identical content (keep highest confidence)
```

### Step 2: Cluster

Clustering groups related memories without predefined categories. Two approaches:

**Approach A: Embedding Clustering (Primary)**

```
For each pair of memories:
  similarity = cosine_similarity(embedding(a), embedding(b))
  If similarity > 0.65:
    a and b belong to the same cluster

Groups are formed by transitive closure:
  If A ≈ B and B ≈ C, then {A, B, C} is a cluster.

Min cluster size: 3
Max cluster size: No limit (but clusters > 8 are likely too broad)
```

**Approach B: LLM Theme Extraction (Secondary, for sparse data)**

When embedding clustering yields no clusters (user has diverse, unrelated memories), an LLM pass looks for abstract themes:

```
Prompt: "Given these memories about a user, identify any common themes or
         patterns. Only identify themes supported by at least 3 memories."
```

This handles cases where memories are not semantically similar but share an abstract commonality (e.g., all relate to "independence" even though the specific topics differ).

**Cluster Example**

```
Memories:
1. "User built local AI chatbot with Ollama"           (episodic, day 1)
2. "User prefers self-hosted over cloud"                (preference, day 5)
3. "User rejected AWS recommendation"                   (procedural, day 12)
4. "User uses SQLite instead of cloud database"         (episodic, day 20)
5. "User values data privacy"                           (semantic, day 30)
6. "User runs everything on local hardware"             (procedural, day 45)

Cluster (cosine > 0.65 between pairs):
  All 6 items cluster → theme: local-first / self-sufficiency / privacy
```

### Step 3: Synthesize

Each cluster is sent to the LLM for insight generation.

**Synthesis Prompt (Conceptual)**

```
You are analyzing a set of memories about a user to generate higher-level insights.
An insight is a hypothesis that explains MULTIPLE observations — it should be
something not directly stated in any single memory, but evident from the pattern.

Cluster of {N} memories:
{memory list}

Generate an insight using this format:
{
  "statement": "Concise single-sentence insight",
  "type": "trait|pattern|contradiction|summary",
  "reasoning": "Brief explanation of how this follows from the memories",
  "naming": "Short label (2-4 words) for quick identification"
}

RULES:
- Do NOT repeat any single memory verbatim as the insight
- Do NOT generate insights from only 1-2 memories (min 3)
- If memories contradict each other, set type to "contradiction"
- If memories don't form a clear pattern, return null
```

**Synthesis Guardrails (Hallucination Prevention)**

| Condition | Action |
|-----------|--------|
| Cluster has < 3 memories | Skip — insufficient evidence |
| All memories from single session | Skip — may be temporary mood |
| Memories span < 7 days | Skip — too brief to be a stable trait |
| LLM returns vague statement ("user likes technology") | Reject — too generic to be useful |
| LLM returns statement too close to a single memory | Reject — not a synthesis |
| LLM returns null | Accept — no insight to generate |

### Step 4: Score

```
insight_confidence = coherence × coverage × specificity × stability

Each factor ∈ [0.0, 1.0]
Result is geometric mean: (a × b × c × d)^(1/4)
```

#### Factor 1: Coherence (C)

How tightly the cluster's memories relate to each other.

```
C = average cosine similarity across all pairs in the cluster
```

| Cluster | Avg pair similarity | Coherence |
|---------|---------------------|-----------|
| All 6 "local-first" items | 0.82 | 0.82 |
| Mixed: 2 local-first + 2 cloud + 2 privacy | 0.45 | 0.45 |
| Random unrelated items | 0.20 | 0.20 (won't form cluster) |

#### Factor 2: Coverage (V)

How much of the user's memory landscape this insight explains. An insight supported by memories spanning multiple types and sessions is stronger.

```
V = type_diversity × temporal_spread

type_diversity = distinct_memory_types / 4  (episodic/semantic/preference/procedural)
temporal_spread = min(1.0, span_days / 90)
```

| Supporting memories | Type diversity | Temporal spread | Coverage |
|--------------------|---------------|-----------------|----------|
| 2 types, 30 days | 2/4 = 0.50 | 30/90 = 0.33 | 0.17 |
| 3 types, 60 days | 3/4 = 0.75 | 60/90 = 0.67 | 0.50 |
| 4 types, 90 days | 4/4 = 1.00 | 90/90 = 1.00 | 1.00 |

#### Factor 3: Specificity (S)

Generic insights are less useful. "User cares about technology" is weak. "User prioritizes local-first, privacy-preserving solutions over convenience" is strong.

```
S = length_penalty × uniqueness_penalty

length_penalty:
  words < 8:   0.50  (too short, likely generic)
  words 8-15:  0.80
  words 16-25: 1.00  (sweet spot)
  words > 25:  0.90  (too verbose, may ramble)

uniqueness_penalty:
  Check against existing insights for overlap > 80% → 0.50
  Else → 1.00
```

| Statement | Words | Specificity |
|-----------|-------|-------------|
| "User likes technology" | 3 | 0.50 |
| "User prefers local AI solutions" | 5 | 0.50 |
| "User values privacy and local control over cloud convenience" | 10 | 0.80 |
| "User prioritizes self-hosted open-source solutions for AI, databases, and infrastructure to maintain privacy and avoid vendor lock-in" | 18 | 1.00 |

#### Factor 4: Stability (T)

How consistent the evidence is over time. An insight supported regularly over months is stronger than one from a burst in a single week.

```
observations_by_week = count_per_week_over_period
variance = std_dev(observations_by_week)
T = 1.0 - min(0.5, variance / mean)

Simplified:
  If evidence spread evenly across period → 1.0
  If all evidence in 1-2 weeks → 0.3
```

| Distribution | Stability |
|-------------|-----------|
| 6 memories evenly across 12 weeks (0.5/week) | 1.0 |
| 6 memories all in week 1, nothing after | 0.3 |
| 6 memories in weeks 1, 3, 5, 7, 9, 11 | 0.9 |

#### Worked Confidence Example

```
Insight: "User values privacy and local control"

Cluster: 6 memories
Coherence: avg pair similarity = 0.82
Coverage:
  types: episodic, preference, procedural, semantic = 4/4 = 1.0
  temporal: first to last = 120 days → 120/90 = capped at 1.0
  V = 1.0 × 1.0 = 1.0
Specificity:
  words = 18 → length = 0.90
  unique = yes → uniqueness = 1.0
  S = 0.90 × 1.0 = 0.90
Stability:
  Even spread across 12 weeks → 0.90

Confidence = (0.82 × 1.0 × 0.90 × 0.90)^(1/4)
           = (0.664)^(1/4)
           = 0.904
```

### Step 5: Validate

Before storing, check for issues.

#### Duplicate Check

Compare new insight against all existing insights:

```
For each existing insight:
  cosine_similarity(embedding(new.statement), embedding(existing.statement))

If > 0.85 → DUPLICATE
  Action: Merge supporting memories into existing insight.
          Recalculate confidence with expanded evidence.
          Bump version number.
          Skip creating new insight.

If > 0.65 but < 0.85 → RELATED
  Action: Link the two insights as related.
          Do not merge.
```

#### Hallucination Check

| Red flag | Detection | Action |
|----------|-----------|--------|
| Insight has no direct support in memories | LLM generated something not in the cluster | Reject insight |
| Insight extrapolates beyond evidence | E.g., "user is an activist" from "user cares about privacy" | Reduce confidence by 0.3 |
| Insight contradicts majority of evidence | Cluster has 5 local-first + 1 cloud → insight says "user likes cloud" | Reject (miscategorized) |
| Insight is a verbatim copy of one memory | Not a synthesis | Reject |
| Insight makes a claim about identity not supported | "User is a developer" from "user built one project" | Reduce confidence to 0.50 (pending) |

#### Contradiction Check

If new insight conflicts with an existing active insight:

```
Existing: "User prefers convenience over privacy" (conf: 0.70, evidence: 4)
New:      "User values privacy and avoids cloud" (conf: 0.82, evidence: 6)

Resolution:
  1. Flag both as "contested"
  2. Link them as contradictions of each other
  3. The one with higher confidence × evidence_count stays active
  4. The other is downgraded to "contested" status
  5. Log the contradiction for future monitoring

Contradictions are valuable — they capture genuine user complexity.
A user can be both privacy-conscious AND convenience-seeking in different contexts.
```

---

## 4. Insight Update Algorithm

```
FUNCTION update_insights(user_id):

    // 1. Gather fresh evidence
    recent_memories = load_memories(user_id, min_confidence=0.50, max_age_days=90)

    IF count(recent_memories) < 3:
        RETURN  // Not enough data to reflect on

    // 2. Load existing insights
    existing_insights = load_insights(user_id)

    // 3. Cluster new memories
    clusters = cluster_by_embedding(recent_memories, threshold=0.65)
    clusters = filter(clusters, min_size=3)

    // 4. For each cluster, attempt insight generation
    FOR each cluster in clusters:

        candidate = synthesize_insight(cluster)
        IF candidate is null: CONTINUE

        candidate.confidence = score_insight(candidate, cluster)

        IF candidate.confidence < MIN_CONFIDENCE (0.50):
            CONTINUE  // Too weak to store

        // 5. Check against existing
        match = find_matching_insight(candidate, existing_insights)

        IF match and match.type != "contradiction":
            // Merge into existing
            match.supporting_memories = union(
                match.supporting_memories,
                candidate.supporting_memories
            )
            match.evidence_count = count(match.supporting_memories)
            match.confidence = recalculate_confidence(match)
            match.version += 1
            match.last_updated = now()
            update_stored_insight(match)

        ELIF match and match.type == "contradiction":
            // Flag both
            mark_contested(match, candidate)

        ELSE:
            // New insight
            candidate.status = "active" if candidate.confidence >= 0.65 else "pending"
            candidate.created_at = now()
            insert_insight(candidate)

    // 6. Decay existing insights not recently reinforced
    FOR each insight in existing_insights:
        days_since_update = (now - insight.last_updated).days

        IF days_since_update > DECAY_DAYS (60):
            insight.confidence *= 0.97 ^ days_since_update

            IF insight.confidence < ARCHIVE_THRESHOLD (0.30):
                insight.status = "archived"
                insight.last_updated = now()
                update_stored_insight(insight)

    // 7. Enforce max insights
    active_insights = filter(existing_insights, status="active")
    IF count(active_insights) > MAX_INSIGHTS (20):
        prune_lowest_confidence(active_insights, target=15)
```

---

## 5. Insight Retrieval

Insights are NOT injected into every prompt — that would be context pollution. They are retrieved only when relevant.

### Retrieval Trigger

```
FUNCTION should_retrieve_insights(query, context):

    // Check for meta-cognitive queries
    IF query matches pattern:
      "what do you know about me"
      "describe me"
      "what kind of person am I"
      "what have you learned about me"
      "tell me about yourself from my perspective"
    → RETURN True (retrieve all active insights, top_k=5)

    // Check for decision-making queries where insight is valuable
    IF query matches pattern:
      "what should I"  (recommendation)
      "recommend"      (recommendation)
      "should I use"   (tool choice)
      "help me decide" (decision support)
    → RETURN True (retrieve relevant insights only, top_k=3)

    // Default: skip insights to avoid context pollution
    → RETURN False
```

### Insight Injection Format

When retrieved, insights are injected into the system prompt:

```
Based on our conversations, here are some observations about you:

- You value privacy and local control. (confidence: very high)
- You prefer concise, direct answers. (confidence: high)
- You adopt new tools quickly. (confidence: moderate)

Use these observations to personalize your response, but do not
state them explicitly to the user unless asked.
```

### Reasoning for the "Don't State" Rule

The user did not explicitly tell Kuro these things. Kuro inferred them from patterns. Stating an insight directly ("I've noticed you value privacy") can feel like:
- Intrusive surveillance ("the AI has been profiling me")
- Incorrect (if the insight is wrong)
- Presumptuous ("don't tell me who I am")

Instead, insights should *shape* the response without being mentioned. E.g., if the insight is "user prefers local tools", Kuro should recommend local tools without saying "I know you prefer local tools."

---

## 6. Insight Invalidation

### When Insights Become Wrong

| Scenario | Trigger | Action |
|----------|---------|--------|
| User explicitly contradicts | "No, I don't care about privacy that much" | Confidence *= 0.3. If below 0.40 → archive. |
| Evidence shifts | Last 10 memories contradict the insight | Recluster. If new cluster conflicts, mark as "contested". |
| Temporal decay | No reinforcement for 60+ days | Gradual decay. Archive at 0.30. |
| User corrects Kuro's behavior | "Stop assuming I want short answers" | Archive all verbosity insights immediately. |

### Correction Prompt Detection

```
FUNCTION detect_correction_signal(message):

    patterns = [
        "don't assume",
        "stop assuming",
        "that's not right",
        "that's wrong",
        "no, I",
        "actually, I don't",
        "why do you think",
        "I never said",
        "you keep",
        "stop doing",
    ]

    IF any(pattern in message.lower()):
        RETURN True
    RETURN False
```

When a correction is detected:
1. Load all active insights
2. Compute relevance of each insight to the correction context
3. Archive the most relevant insight
4. Log the invalidation event

### Invalidation Record

```
{
  "insight_id": "ins_04n7...",
  "reason": "user_correction",
  "trigger_message": "No, I don't actually care that much about self-hosting",
  "previous_confidence": 0.82,
  "evidence_count_at_invalidation": 6,
  "archived_at": "2026-07-01T10:00:00Z",
  "can_revive": false
}
```

Invalidated insights are preserved in an archived section (not deleted) for:
- Audit trail
- Potential revival if evidence re-emerges
- Analysis of why the system was wrong

---

## 7. Hallucination Prevention Summary

| Layer | Mechanism | What it prevents |
|-------|-----------|------------------|
| **Input** | Min cluster size = 3 | Insights from coincidental single pairs |
| **Input** | Min temporal span = 7 days | Insights from short-term moods |
| **Synthesis** | LLM guardrails: reject vague/duplicate/null | Low-quality insight generation |
| **Scoring** | Coherence factor | Insights from loosely related memories |
| **Scoring** | Coverage factor | Insights from narrow evidence base |
| **Scoring** | Stability factor | Insights from temporal flukes |
| **Validation** | Duplicate check (0.85 cosine) | Redundant insights |
| **Validation** | Hallucination checks | LLM over-extrapolation |
| **Threshold** | Min confidence = 0.50 for storage | Weak insights never stored |
| **Threshold** | Min confidence = 0.65 for active | Uncertain insights not applied |
| **Retrieval** | Only retrieved for meta/decision queries | Context pollution |
| **Application** | Shape behavior, never state | Creepiness, presumptuousness |
| **Decay** | 60-day decay without reinforcement | Stale insights persist |
| **Correction** | User correction → immediate archive | Wrong insights remain active |

---

## 8. Full Worked Example

### User Journey Across 3 Months

**Day 1-30: Initial Memories**
```
Memories accumulated:
  "User built local chatbot with Ollama" (episodic)
  "User prefers self-hosted" (preference)
  "User rejected AWS" (procedural)
  "User uses SQLite" (episodic)
  "User values privacy" (semantic)
```

**Day 30: First Reflection Run**
```
Cluster: all 5 memories → coherence 0.78
Insight: "User values privacy and local control"
  Confidence: 0.74 → ACTIVE
  Supporting: 5 memories, 3 types, 30-day span
```

**Day 45: More Evidence**
```
New memories:
  "User chose self-hosted Git over GitHub" (episodic)
  "User dislikes vendor lock-in" (preference)
  "User runs everything on local hardware" (procedural)

Reflection update:
  Same cluster, now 8 memories
  Confidence recalculated: 0.85 → still ACTIVE, stronger
  Version bumped to 2
```

**Day 60: Contradictory Evidence**
```
New memory:
  "User uses ChatGPT (cloud)" (episodic)
  "Cloud AI is convenient sometimes" (preference)

Reflection update:
  Contradiction detected: evidence_count = 8 local + 2 cloud
  Existing insight marked as "contested"
  New insight generated: "User balances privacy with pragmatism"
  Confidence: 0.58 → PENDING (below 0.65)
  Two insights now coexist, linked as contradictions
```

**Day 90: Resolution**
```
If more local evidence: local insight remains active, pragmatism insight decays
If more cloud evidence: local insight decays, pragmatism insight may activate
If mixed: both remain contested → reflects genuine user complexity
```

**Day 120: User Correction**
```
User: "You know what, I've been using cloud more lately. Privacy isn't as important to me now."
Kuro detects correction signal
Local-privacy insight: confidence *= 0.3 → 0.24 → ARCHIVED
Pragmatism insight: no longer contested, confidence boosted to 0.62 → PENDING

System learns: user's values shifted over time. Insights are not permanent.
```
