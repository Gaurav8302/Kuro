# Kuro AI — Procedural Memory System

## Purpose

The other memory layers (episodic, semantic, preference) answer *what* the user knows, likes, and has done. Procedural memory answers *how* the user behaves — it detects repeated interaction patterns and converts them into rules that shape Kuro's future responses.

**Key insight**: A user who repeatedly says "just the short version" or "TL;DR" doesn't need a semantic memory saying "user likes short answers". They need a procedural rule: `WHEN user asks for information → PREFER concise response`. That rule persists across sessions and applies automatically.

---

## 1. System Overview

```
User Action
    │
    ▼
┌──────────────────────┐
│  Pattern Detector     │  ← Observes user behavior over time
│  (statistical, not    │
│   per-fact storage)   │
└──────┬───────────────┘
       │ repeated observation
       ▼
┌──────────────────────┐
│  Rule Generator       │  ← Converts pattern into actionable rule
│  (confidence ≥        │
│   threshold)          │
└──────┬───────────────┘
       │ new/updated rule
       ▼
┌──────────────────────┐
│  Rule Store           │  ← Persistent JSON storage
│  (user → rules[])    │
└──────┬───────────────┘
       │ on each turn
       ▼
┌──────────────────────┐
│  Rule Applicator      │  ← Checks active rules before response
│  (applies matching    │
│   rules to behavior)  │
└──────┬───────────────┘
       │ behavior instruction
       ▼
┌──────────────────────┐
│  Response Generation  │
└──────────────────────┘
```

---

## 2. Key Concepts

### What Procedural Memory Learns

| Pattern Category | Example | Rule |
|-----------------|---------|------|
| **Verbosity preference** | User consistently says "keep it short", "TL;DR", "summarize" | `WHEN responding → PREFER concise` |
| **Naming convention** | User shortens names: "AI Research Lab" → "AI Lab" | `WHEN entity name → SHORTEN to convention` |
| **Format preference** | User asks for "bullet points", "steps", "numbered list" | `WHEN listing → USE user's preferred format` |
| **Tool preference** | User repeatedly recommends local tools over cloud | `WHEN tool recommendation → BIAS toward local` |
| **Response structure** | User prefers "first the answer, then explanation" | `WHEN responding → STRUCTURE answer-first` |
| **Coding style** | User consistently uses tabs over spaces, semicolons | `WHEN generating code → USE user's style` |
| **Addressing style** | User prefers "hey" over "hello", or no greetings | `WHEN greeting → MATCH user's style` |
| **Depth preference** | User asks "details?" or "explain more" vs "move on" | `WHEN explaining → ADJUST depth to pattern` |

### What It Does NOT Learn

| Signal | Why excluded |
|--------|-------------|
| Single-instance requests | "Can you explain that differently?" → may be one-off |
| Mood-dependent behavior | "I'm too tired for this today" → temporary state |
| Contradictory signals | If user both asks for short and detailed answers equally → no clear pattern |
| Explicit one-time instructions | "From now on, call me Alex" → this is a preference, handled by semantic memory |

---

## 3. Data Structures

### Observation Journal (Raw Input)

```
{
  "user_id": "user_abc123",
  "observations": [
    {
      "id": "obs_01j5...",
      "pattern_id": "pat_verbosity_001",
      "category": "verbosity",
      "signal": "concise_request",
      "trigger_phrase": "keep it short",
      "turn_count": 47,
      "session_id": "sess_xyz",
      "timestamp": "2026-06-15T14:30:00Z",
      "context": {
        "query_length": 85,
        "response_length": 312,
        "topic": "explanation"
      }
    }
  ]
}
```

### Pattern Definition (Learned Structure)

```
{
  "id": "pat_verbosity_001",
  "user_id": "user_abc123",
  "category": "verbosity",
  "name": "prefers_concise_responses",
  "description": "User consistently prefers short, direct answers over detailed explanations",

  "trigger_signals": {
    "phrases": [
      "keep it short",
      "TL;DR",
      "too long",
      "summarize",
      "short version"
    ],
    "actions": [
      "asks_for_summary_after_long_response",
      "stops_reading_mid_response"
    ],
    "context_filters": {
      "topic_exclude": ["technical_debugging", "medical"],
      "min_occurrences": 3
    }
  },

  "behavior_rule": {
    "type": "response_style",
    "target": "verbosity",
    "value": "concise",
    "parameters": {
      "max_sentences": 3,
      "prefer_bullets": false,
      "include_summary_first": true
    }
  },

  "confidence": 0.82,
  "evidence_count": 7,
  "first_detected": "2026-04-10T09:00:00Z",
  "last_observed": "2026-06-18T16:45:00Z",
  "observation_interval_days": 69,
  "is_active": true
}
```

### Rule Store (Persistent JSON)

```
{
  "version": 1,
  "user_id": "user_abc123",
  "rules": [
    { pattern object },
    { pattern object }
  ],
  "global": {
    "min_confidence_for_activation": 0.60,
    "observation_window_days": 90,
    "max_rules_per_user": 30
  }
}
```

### Behavioral Signature (Compact Index for Fast Matching)

```
{
  "user_id": "user_abc123",
  "signatures": {
    "verbosity": {
      "current": "concise",
      "confidence": 0.82,
      "status": "active"
    },
    "naming": {
      "current": "shortens_acronyms",
      "confidence": 0.71,
      "status": "active"
    },
    "code_style": {
      "current": null,
      "confidence": 0.0,
      "status": "insufficient_data"
    },
    "format": {
      "current": "bullets",
      "confidence": 0.65,
      "status": "active"
    },
    "greeting": {
      "current": "casual",
      "confidence": 0.90,
      "status": "active"
    }
  }
}
```

---

## 4. Learning Algorithm

### Algorithm: Accumulate → Detect → Generalize → Confirm

```
PHASE 1: ACCUMULATE (per turn)

On every conversation turn:
  1. Extract behavioral signals from the exchange
  2. Classify each signal into a pattern category
  3. Store as an Observation in the journal
  4. Hash the observation for dedup (avoid counting the same phrase twice)

PHASE 2: DETECT (when journal reaches threshold)

Triggered when any category reaches MIN_OBSERVATIONS (default: 3):

  For each category:
    1. Gather all observations in that category (last 90 days)
    2. Group by signal type (phrase, action, context)
    3. Compute occurrence frequency:
         frequency = count / total_observations_in_category
    4. If frequency >= MIN_FREQUENCY (0.60):
         → Candidate pattern detected


PHASE 3: GENERALIZE (convert observations to rule)

  For each candidate pattern:
    1. Extract common trigger conditions
       (phrases that precede the behavior, contexts where it occurs)
    2. Formulate the rule template:
       WHEN {trigger_conditions} → APPLY {behavior_rule}
    3. Compute initial confidence (see Section 5)
    4. If confidence >= ACTIVATION_THRESHOLD (0.60):
         → Store as active rule
    5. Else:
         → Store as pending rule (continue observing)

PHASE 4: CONFIRM (reinforce or decay)

  On each subsequent observation that matches an existing rule:
    1. Increment evidence_count
    2. Update last_observed timestamp
    3. Recalculate confidence (upward adjustment)
    4. If rule was pending and now >= threshold → activate it

  If 30 days pass without matching observation:
    1. Apply decay to confidence
    2. If confidence drops below DECAY_THRESHOLD (0.30):
         → Archive the rule (inactive, not deleted)
```

### Detailed Detection Logic

#### Verbosity Pattern Detection

```
Input observations for category "verbosity":

[
  { signal: "concise_request", phrase: "keep it short",     turn: 12 },
  { signal: "concise_request", phrase: "TL;DR",             turn: 28 },
  { signal: "concise_request", phrase: "too long",          turn: 35 },
  { signal: "detail_request",  phrase: "tell me more",     turn: 41 },
  { signal: "concise_request", phrase: "summarize",         turn: 52 },
  { signal: "concise_request", phrase: "short version",    turn: 67 },
  { signal: "concise_request", phrase: "way too verbose",   turn: 73 },
]

Total verbosity observations: 7
Total observations in category: 8 (including 1 detail_request)
Concise ratio: 7/8 = 0.875

THRESHOLD CHECK:
  0.875 >= 0.60 → YES, candidate pattern

OUTPUT:
  pattern_id: pat_verbosity_001
  category: verbosity
  rule: WHEN responding → PREFER concise (max 3 sentences, summary-first)
  confidence: computed in Section 5
```

#### Naming Convention Detection

```
Input observations for category "naming":

[
  { signal: "shortened_name", original: "Artificial Intelligence Research Lab",
                                shortened: "AI Research Lab",       turn: 20 },
  { signal: "shortened_name", original: "National Science Foundation",
                                shortened: "NSF",                   turn: 33 },
  { signal: "shortened_name", original: "Machine Learning Operations",
                                shortened: "MLOps",                 turn: 45 },
  { signal: "no_shortening",  original: "Project Kuro",
                                response: "Project Kuro",            turn: 50 },
  { signal: "shortened_name", original: "Convolutional Neural Network",
                                shortened: "CNN",                   turn: 61 },
]

Naming observations: 5
Shortening ratio: 4/5 = 0.80

PATTERN DETECTED:
  User shortens multi-word proper nouns to acronyms or abbreviated forms.

RULE GENERATED:
  WHEN entity has multi-word name → PREFER acronym/shortened form
  (store the mapping pair for known entities)
```

#### Tool Preference Detection

```
Input observations for category "tool_preference":

[
  { signal: "endorsed_local", tool: "Ollama",      cloud_alt: "OpenAI",   turn: 15 },
  { signal: "endorsed_local", tool: "LocalAI",     cloud_alt: null,       turn: 27 },
  { signal: "rejected_cloud", tool: null,           cloud_alt: "AWS",     turn: 42 },
  { signal: "endorsed_local", tool: "llama.cpp",   cloud_alt: "Groq",    turn: 58 },
  { signal: "rejected_cloud", tool: null,           cloud_alt: "GCP",     turn: 63 },
  { signal: "endorsed_local", tool: "SQLite",       cloud_alt: "Cloud DB", turn: 70 },
]

Local endorsements: 4
Cloud rejections: 2
Total tool preference signals: 6
Local preference ratio: 4/6 = 0.67

PATTERN DETECTED (borderline):
  0.67 >= 0.60 → YES, but barely

RULE GENERATED:
  WHEN recommending tools → BIAS toward self-hosted/local options
  (confidence will be moderate due to mixed signals)
```

---

## 5. Confidence Scoring

### Formula

```
confidence = base × consistency × recency × specificity

Each factor ∈ [0.0, 1.0]
Result clamped to [0.0, 1.0]
```

#### Factor 1: Base Evidence (B)

```
B = min(1.0, evidence_count / EVIDENCE_TARGET)

EVIDENCE_TARGET = 8 (the number of observations needed for max base)
```

| Evidence count | Base |
|----------------|------|
| 1 | 0.125 |
| 3 | 0.375 |
| 5 | 0.625 |
| 8 | 1.000 |
| 12 | 1.000 |

#### Factor 2: Consistency (C)

Measures how uniform the signal is. A pattern with 8 concise-request observations and 0 detail-requests is stronger than one with 5 concise and 3 detail.

```
C = (dominant_signal_count - noise_count) / total_count

Where:
  dominant_signal = the signal type being detected (e.g., "concise_request")
  noise = opposing or contradictory signals (e.g., "detail_request")
  total = all observations in category
```

| Signal mix | Consistency |
|---|---|
| 8 concise, 0 detail | (8-0)/8 = 1.00 |
| 7 concise, 1 detail | (7-1)/8 = 0.75 |
| 5 concise, 3 detail | (5-3)/8 = 0.25 → below threshold |
| 4 concise, 4 detail | (4-4)/8 = 0.00 → NO PATTERN |

#### Factor 3: Recency (R)

More recent observations are stronger evidence.

```
R = 0.5 ^ (days_since_last_observation / 30)
```

| Days since last observation | Recency |
|---|---|
| 0 (today) | 1.00 |
| 7 (week ago) | 0.84 |
| 30 (month ago) | 0.50 |
| 90 (3 months ago) | 0.12 |
| 180 (6 months ago) | 0.02 |

#### Factor 4: Specificity (S)

Generic patterns are weaker than specific ones. "User shortens names" → medium. "User shortens AI/ML organization names to acronyms" → stronger.

```
S = 0.60 + (context_tags_count × 0.10)
S ∈ [0.60, 1.00]
```

| Pattern specificity | Tags example | Specificity |
|---|---|---|
| Generic | ["verbosity"] | 0.60 |
| Moderate | ["verbosity", "explanation"] | 0.70 |
| Specific | ["verbosity", "explanation", "technical"] | 0.80 |
| Highly specific | ["verbosity", "explanation", "technical", "short_query"] | 0.90 |

#### Worked Examples

**Example A: Strong verbosity pattern**
```
evidence_count = 7     → B = min(1.0, 7/8)      = 0.875
consistency:
  7 concise, 1 detail  → C = (7-1)/8             = 0.750
last observed: 2 days ago → R = 0.5^(2/30)       = 0.955
context_tags: ["verbosity", "explanation"] → S   = 0.70

confidence = 0.875 × 0.750 × 0.955 × 0.70
           = 0.439
Wait, this seems low for a strong pattern. Let me reconsider the formula.

Actually, the multiplicative approach is too aggressive. Let's use a weighted sum
of log-transformed factors, or better: a geometric mean approach.

Revised formula:
confidence = (B × C × R × S)^(1/4)

This gives the geometric mean, which is more appropriate for combining
independent factors multiplicatively but scaling back to [0,1].

Revised Example A:
  confidence = (0.875 × 0.750 × 0.955 × 0.70)^(1/4)
             = (0.439)^(1/4)
             = 0.813

This is more reasonable — a strong pattern with good evidence.
```

**Example B: Weak/emerging pattern**
```
evidence_count = 3     → B = min(1.0, 3/8)       = 0.375
consistency:
  3 concise, 2 detail  → C = (3-2)/5             = 0.200
last observed: 10 days ago → R = 0.5^(10/30)     = 0.794
context_tags: ["verbosity"] → S                   = 0.60

confidence = (0.375 × 0.200 × 0.794 × 0.60)^(1/4)
           = (0.036)^(1/4)
           = 0.435

Below 0.60 threshold. Pattern stored as pending.
```

**Example C: Very strong, consistent, recent pattern**
```
evidence_count = 12    → B = 1.000
consistency:
  12 concise, 0 detail → C = (12-0)/12           = 1.000
last observed: today   → R = 1.000
context_tags: ["verbosity", "explanation", "technical", "short_query"] → S = 0.90

confidence = (1.000 × 1.000 × 1.000 × 0.90)^(1/4)
           = (0.90)^(1/4)
           = 0.974
```

### Thresholds

| Confidence | Status | Action |
|------------|--------|--------|
| 0.00–0.39 | None | Insufficient evidence, ignore |
| 0.40–0.59 | Pending | Stored but inactive, continue observing |
| 0.60–0.79 | Active (moderate) | Apply rule, review quarterly |
| 0.80–1.00 | Active (strong) | Apply rule consistently |

---

## 6. Rule Generation

### Rule Templates

Each pattern category maps to a rule template with parameters.

```
VERBOSITY:
  Template:  WHEN responding → SET verbosity = {value}
  Values:    ["concise", "balanced", "detailed"]
  Example:   WHEN responding → SET verbosity = "concise"
             Effect: Kuro limits responses to 3 sentences, puts conclusion first

NAMING_CONVENTION:
  Template:  WHEN entity_name {entity} → USE form {preferred_form}
  Values:    {entity: string, preferred_form: string}
  Example:   WHEN entity_name "Artificial Intelligence Research Lab"
             → USE form "AI Research Lab"
  Effect:    Kuro uses the user's preferred name for known entities

FORMAT_PREFERENCE:
  Template:  WHEN response_type = {type} → USE format {format}
  Values:    {type: ["list", "comparison", "explanation"],
              format: ["bullets", "numbered", "paragraph", "table"]}
  Example:   WHEN response_type = "list" → USE format "bullets"
  Effect:    Kuro formats lists as bullet points instead of paragraphs

TOOL_BIAS:
  Template:  WHEN recommending {domain} tools → BIAS toward {preference}
  Values:    {domain: ["general", "ai", "database", "hosting"],
              preference: ["local", "cloud", "open_source", "enterprise"]}
  Example:   WHEN recommending "ai" tools → BIAS toward "local"
  Effect:    Kuro prioritizes local/self-hosted tools in recommendations

GREETING_STYLE:
  Template:  WHEN greeting → USE style {style}
  Values:    ["casual", "formal", "none"]
  Example:   WHEN greeting → USE style "casual"
  Effect:    Kuro starts with "hey" or "hi" rather than "hello" or "greetings"

CODING_STYLE:
  Template:  WHEN generating {language} code → USE style {style_config}
  Values:    {style_config: {indentation, quotes, semicolons, naming}}
  Example:   WHEN generating "python" code
             → USE style {indentation: "spaces", quotes: "single"}
  Effect:    Kuro matches the user's observed coding conventions

DEPTH_PREFERENCE:
  Template:  WHEN user asks {topic_type} question → RESPOND with depth {level}
  Values:    {level: ["shallow", "moderate", "deep"]}
  Example:   WHEN user asks "definition" question → RESPOND with depth "shallow"
  Effect:    Kuro provides brief definitions rather than deep dives
```

### Rule Merging

When a new rule would conflict with an existing one:

| Existing | New | Resolution |
|----------|-----|------------|
| concise (conf: 0.81) | detailed (conf: 0.45) | Keep concise, trust higher confidence |
| concise (conf: 0.65) | detailed (conf: 0.70) | Conflict detected. Flag for review. Neither applied automatically. |
| concise (conf: 0.81, 2mo old) | concise (conf: 0.73, fresh) | Merge: update timestamps, average confidence |

---

## 7. Rule Application

### At Response Time

```
FUNCTION apply_procedural_rules(user_id, current_context):

    rules = load_active_rules(user_id)
    applicable = []

    FOR each rule in rules:

        // Check trigger conditions
        trigger_match = evaluate_rule_triggers(
            rule.trigger_signals,
            current_context
        )

        IF trigger_match.score >= TRIGGER_THRESHOLD (0.50):
            applicable.append({
                "rule": rule,
                "match_score": trigger_match.score,
                "behavior_instruction": rule.behavior_rule
            })

    // Resolve conflicts
    applicable = resolve_conflicts(applicable)

    // Convert to behavior instructions for the LLM
    behavior_instructions = [
        format_instruction(a.rule) for a in applicable
    ]

    RETURN behavior_instructions
```

### Trigger Evaluation

```
FUNCTION evaluate_rule_triggers(signals, context):

    score = 0.0
    checks = 0

    // Check phrase triggers
    IF signals.phrases:
        FOR phrase in signals.phrases:
            IF phrase in context.user_message.lower():
                score += 1.0
        checks += 1

    // Check action triggers
    IF signals.actions:
        FOR action in signals.actions:
            IF action in context.observed_actions:
                score += 1.0
        checks += 1

    // Check context filters (negative)
    IF signals.context_filters.topic_exclude:
        IF context.topic in signals.context_filters.topic_exclude:
            score -= 2.0  // Strong veto
        checks += 1

    RETURN normalize(score / checks)
```

### Behavior Instruction Format

Rules are injected as structured behavior instructions in the system prompt:

```
User behavior patterns observed:

- When explaining technical concepts, user prefers short answers.
  → Keep responses concise. Lead with the answer, not the background.

- User shortens organization names to acronyms.
  → Use "AI Research Lab" instead of "Artificial Intelligence Research Lab",
    "NSF" instead of "National Science Foundation".

- User prefers local/self-hosted tools over cloud services.
  → When recommending tools, prioritize self-hosted options.
    Only suggest cloud services as alternatives, not defaults.

These patterns were learned from {N} previous conversations.
Only apply them when the current context matches.
```

### Position in Prompt

Procedural rules live in the system prompt, NOT the memory context block. This is critical:

| Injection point | Why |
|----------------|-----|
| System prompt (top) | Rules shape behavior from the start |
| Not in memory block | Memory is for facts; rules are for behavior |
| Before user message | LLM sees rules before processing the query |

### Rule vs Fact: When to Use Each

| Scenario | Layer | Reason |
|----------|-------|--------|
| User asks "What's my name?" | Semantic memory | Direct fact lookup |
| User says "I prefer local tools" | Preference memory | Explicit preference statement |
| User repeatedly shortens names over 7 sessions | Procedural memory | Behavioral pattern, not stated preference |
| User says "Can you make it shorter?" once | Neither | Single instance, insufficient evidence |
| User always responds negatively to cloud recommendations | Procedural memory | Observed behavior across multiple recommendations |

---

## 8. Observation Journal (Detailed)

### Schema

```
{
  "user_id": "user_abc123",
  "observations": [ ... ],
  "stats": {
    "total_observations": 142,
    "first_observation": "2026-01-15T10:00:00Z",
    "last_observation": "2026-06-20T14:30:00Z",
    "active_rules": 5,
    "pending_rules": 2,
    "archived_rules": 1
  }
}
```

### Observation Categories and Signals

| Category | Signals to detect | Trigger phrases/examples |
|----------|-------------------|--------------------------|
| `verbosity` | `concise_request`, `detail_request` | "too long", "TL;DR", "tell me more", "explain in detail" |
| `naming` | `shortened_name`, `uses_acronym`, `full_name_preference` | User writes "ML" after assistant wrote "Machine Learning" |
| `format` | `prefers_bullets`, `prefers_paragraph`, `prefers_tables` | "Can you list that?", "put it in a table" |
| `greeting` | `casual_greeting`, `formal_greeting`, `no_greeting` | "hey", "sup", "good morning", (silence on greeting) |
| `tool_bias` | `endorsed_local`, `endorsed_cloud`, `rejected_cloud`, `rejected_local` | "I just use Ollama", "cloud is too expensive" |
| `depth` | `shallow_followup`, `deep_followup` | User moves on quickly vs asks "tell me more" |
| `code_style` | `indentation_style`, `quote_style`, `naming_convention` | User provides code snippets with consistent style |
| `tone` | `casual_tone`, `formal_tone`, `humorous`, `direct` | "lol", "btw", user's general phrasing style |

---

## 9. Edge Cases

### Edge Case 1: Cold Start (No Data)

**Situation**: New user, zero observations.

**Behavior**: No procedural rules generated. Rule Applicator returns empty list. System prompt proceeds without behavior instructions. System logs `procedural: cold_start`.

### Edge Case 2: Contradictory Patterns

**Situation**: User both requests concise and detailed answers with equal frequency.

```
Observations:
  5 concise requests ("TL;DR", "keep it short")
  5 detail requests ("explain more", "tell me in detail")
```

**Behavior**: Consistency score: (5-5)/10 = 0.00. No rule generated for either pattern. System flags this as "conflicting signals" — no action needed, but logged. User may be context-dependent (wants short answers for definitions, details for technical topics).

**Future improvement**: Add topic-level context to distinguish. Same user: concise for definitions, detailed for debugging.

### Edge Case 3: Pattern Reversal

**Situation**: User had strong verbosity=concise pattern (confidence 0.85), then suddenly starts asking for detailed explanations.

```
Last 5 observations (all detail requests):
  "explain that more thoroughly"
  "I need more context"
  "that was too brief"
  "can you elaborate"
  "give me the full picture"
```

**Behavior**: Confidence decays as observations shift. Consistency recalculates:
```
Old: 12 concise, 1 detail  → C = 0.85  → rule active
Now: 12 concise, 6 detail  → C = 0.33  → rule pending (below threshold)
```

After 6 contradictory observations, the rule downgrades from active to pending. After 10, it archives. The system adapts to the user's changing preferences — it does NOT permanently lock in a pattern.

### Edge Case 4: User Corrects the Pattern

**Situation**: User says "Stop shortening things. I want the full names."

**Behavior**: This is a DIRECTIVE, which is stronger than an observed pattern.

1. The directive is detected as a `pattern_reset` signal
2. All rules in the `naming` category get `confidence *= 0.3`
3. If confidence drops below 0.40, rule is archived
4. The directive itself is NOT stored as a rule (it's a fact, goes to episodic memory)
5. The system starts fresh observation for naming patterns

### Edge Case 5: Single-Session Pattern

**Situation**: User exhibits a behavior pattern 6 times within one intense session, then never again.

```
Session 1: 6 concise requests
Sessions 2-10: 0 concise requests
```

**Behavior**: The pattern would temporarily become active (6 observations → confidence ~0.70). But over 30 days without reinforcement, recency decays:
```
After 30 days: R = 0.5, new confidence ≈ 0.59 → pending
After 60 days: R = 0.25, new confidence ≈ 0.42 → pending (nearly archived)
```

The system correctly distinguishes between a genuine habit and a one-session mood. If the user truly has a pattern, it will re-emerge; if not, it fades.

### Edge Case 6: Topic-Constrained Patterns

**Situation**: User only wants short answers about technical topics, but deep dives on creative topics.

**Behavior**: The basic system would struggle with this — it sees mixed signals. The context-aware enhancement adds topic tags to each observation, enabling topic-conditional rules.

```
WHEN topic = "technical" → verbosity = "concise"   (conf: 0.85)
WHEN topic = "creative" → verbosity = "detailed"   (conf: 0.78)
```

This requires a richer observation schema but handles real user behavior far better.

### Edge Case 7: Maximum Rules Reached

**Situation**: User has 30 active rules (the cap).

**Behavior**: System enters maintenance mode:
1. Sort rules by confidence × recency
2. Archive the lowest-scoring rule
3. Add the new rule
4. Log the replacement

This ensures the rule set stays fresh and relevant.

---

## 10. Full Worked Example

### Scenario: New User Across 3 Sessions

**Session 1 (Day 1)**:
```
User: "Hey"
Kuro: "Hello! How can I help you?"
User: "Explain neural networks"
Kuro: [long detailed explanation]
User: "TL;DR. Just give me the short version."
Kuro: "Neural networks are pattern-matchers. They learn from data."
User: "Also, I use Ollama for everything. Cloud AI is too expensive."
```

Observations recorded:
- greeting: "casual" (hey)
- verbosity: "concise_request" (TL;DR)
- tool_bias: "endorsed_local" (Ollama)
- tool_bias: "rejected_cloud" (cloud too expensive)

**Session 2 (Day 5)**:
```
User: "What's the difference between SQL and NoSQL?"
Kuro: [concise 3-sentence explanation]  ← already adjusting!
User: "Good. That was perfect."
User: "Also I just use SQLite. Don't need a cloud database."
```

Observations recorded:
- verbosity: feedback positive on concise
- tool_bias: "endorsed_local" (SQLite)

**Session 3 (Day 12)**:
```
User: "Compare React and Vue"
Kuro: [concise 2-sentence answer + bullet points] ← procedural rules applied
User: "What about cost?"
Kuro: "For local-first projects, both are free. [local tool bias applied]"
```

**After Session 3 — Rule Generation**:

```
Rule 1: verbosity→concise
  Evidence: 3 observations (TL;DR, positive feedback, responded well to short)
  Consistency: 3 concise, 0 detail = 1.00
  Confidence: (min(1,3/8) × 1.0 × 0.5^(7/30) × 0.60)^(1/4)
            = (0.375 × 1.0 × 0.848 × 0.60)^(1/4)
            = (0.191)^(1/4)
            = 0.661  → ACTIVE

Rule 2: tool_bias→local
  Evidence: 3 observations (Ollama endorsement, cloud rejection, SQLite)
  Consistency: 2 local + 1 cloud_reject = 3 consistent, 0 contradictory
  Confidence: (0.375 × 1.0 × 0.848 × 0.70)^(1/4)
            = (0.223)^(1/4)
            = 0.688  → ACTIVE

Rule 3: greeting→casual
  Evidence: 1 observation (needs more data)
  Confidence: pending
```

**Session 4 (Day 20) — Rules Applied**:
```
System prompt includes:
  - User prefers concise explanations. Lead with the answer.
  - User prefers local/self-hosted tools. Prioritize them.

User: "I need a database for my new project"
Kuro: "SQLite is great for local-first. If you need more, PostgreSQL.
       Both self-hosted."  ← procedural rule applied, cloud options offered
                              as secondary rather than primary
```
