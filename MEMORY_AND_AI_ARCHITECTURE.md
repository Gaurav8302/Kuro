# Kuro AI - Memory System & AI Model Architecture

> **Comprehensive Technical Documentation**
> 
> Last Updated: February 2026

---

## Table of Contents

1. [Overview](#overview)
2. [AI Model Architecture](#ai-model-architecture)
   - [4-Model Strategy](#4-model-strategy)
   - [Model Details](#model-details)
   - [Routing System](#routing-system)
   - [Fallback & Circuit Breaker](#fallback--circuit-breaker)
3. [Memory System Architecture](#memory-system-architecture)
   - [Layered Memory Design](#layered-memory-design)
   - [Vector Storage (Pinecone)](#vector-storage-pinecone)
   - [Progressive Summarization](#progressive-summarization)
   - [Context Rehydration](#context-rehydration)
4. [Orchestration Flow](#orchestration-flow)
5. [External Services](#external-services)
6. [Configuration Reference](#configuration-reference)

---

## Overview

Kuro AI is a **production-grade, multi-model AI chatbot** featuring:
- **Intelligent Model Routing**: Dynamically selects the best AI model based on query type
- **Semantic Memory**: Long-term conversation context using vector embeddings
- **Resilient Fallback Chains**: Automatic recovery when models fail
- **Progressive Summarization**: Compresses older conversations to maintain context

**Tech Stack:**
- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript
- **Database**: MongoDB (chat history, sessions) + Pinecone (vector embeddings)
- **AI Providers**: Groq (primary) + OpenRouter (fallback)
- **Embeddings**: Google Gemini `text-embedding-004`

---

## AI Model Architecture

### 4-Model Strategy

Kuro uses a **simplified flagship model strategy** with one specialized model per skill:

| Skill | Model | Provider | Purpose | Latency |
|-------|-------|----------|---------|---------|
| **Conversation** | `llama-3.3-70b-versatile` | Groq | Fast, natural chat responses | ~800ms |
| **Reasoning** | `deepseek-r1-distill-llama-70b` | Groq | Complex problem-solving, math, analysis | ~2000ms |
| **Code** | `llama-3.1-8b-instant` | Groq | Code generation, debugging, explanations | ~1000ms |
| **Summarization** | `mixtral-8x7b-32k` | Groq | Memory compression, long document handling | ~1200ms |

### Model Details

#### 1. Conversation Model - LLaMA 3.3 70B Versatile
```yaml
id: llama-3.3-70b-versatile
label: kimmi-conversational
capabilities: [conversation, fast, low_latency, general, casual]
max_context_tokens: 16384
quality_tier: high
cost_score: 3
fallback: ["moonshotai/kimi-dev-72b:free"]
```
- **Use Cases**: General chat, greetings, casual conversation, Q&A
- **Strengths**: Low latency (~800ms), high-quality responses, natural dialogue
- **When Selected**: Default for all queries without specific skill patterns

#### 2. Reasoning Model - DeepSeek R1 Distill LLaMA 70B
```yaml
id: deepseek-r1-distill-llama-70b
label: deepseek-reasoning
capabilities: [complex_reasoning, long_context, math, analysis]
max_context_tokens: 32768
quality_tier: high
cost_score: 5
fallback: ["llama-3.3-70b-versatile"]
```
- **Use Cases**: Math problems, logical puzzles, step-by-step analysis, fact-checking
- **Strengths**: Chain-of-thought reasoning, large context window (32K tokens)
- **When Selected**: Queries containing "solve", "prove", "analyze", "step by step", "logic"

#### 3. Code Model - LLaMA 3.1 8B Instant
```yaml
id: llama-3.1-8b-instant
label: groq-code
capabilities: [code, explain_code, run_thought, debugging]
max_context_tokens: 16384
quality_tier: high
cost_score: 4
fallback: ["deepseek-r1-distill-llama-70b"]
```
- **Use Cases**: Code generation, debugging, code explanations, programming help
- **Strengths**: Fast inference for code tasks, understands multiple languages
- **When Selected**: Queries with code blocks (` ``` `), "debug", "function", "class", "error"

#### 4. Summarization Model - Mixtral 8x7B 32K
```yaml
id: mixtral-8x7b-32k
label: summarizer-memory
capabilities: [summarization, memory, compression, long_context]
max_context_tokens: 32768
quality_tier: medium
cost_score: 2
fallback: ["llama-3.3-70b-versatile"]
```
- **Use Cases**: Document summarization, memory compression, TL;DR generation
- **Strengths**: 32K context window, efficient compression, cost-effective
- **When Selected**: Queries with "summarize", "tl;dr", "condense", or context > 20K tokens

### Routing System

The routing system (`model_router_v2.py`) uses a **priority-based selection**:

```
┌─────────────────────────────────────────────────────────────┐
│                    ROUTING PRIORITY                         │
├─────────────────────────────────────────────────────────────┤
│ 1. Forced Override     → Developer/user specifies model     │
│ 2. Cache Hit           → Recent identical query (TTL: 5min) │
│ 3. Intent Mapping      → classify_intent() → skill          │
│ 4. Keyword Detection   → Regex patterns → skill             │
│ 5. Score-Based         → (Optional, experimental)           │
│ 6. Default             → Conversation model                 │
└─────────────────────────────────────────────────────────────┘
```

#### Intent-to-Skill Mapping
```python
INTENT_TO_SKILL = {
    # Conversation intents
    "casual_chat": "conversation",
    "greeting": "conversation",
    "chitchat": "conversation",
    
    # Reasoning intents
    "complex_reasoning": "reasoning",
    "math_solver": "reasoning",
    "fact_check": "reasoning",
    
    # Code intents
    "code_generation": "code",
    "debugging": "code",
    "explain_code": "code",
    
    # Summarization intents
    "long_context_summary": "summarization",
    "memory": "summarization",
}
```

#### Keyword Pattern Detection
```python
SKILL_KEYWORD_PATTERNS = {
    "code": [r"```", r"\bcode\b", r"\bdebug\b", r"\bfunction\b", r"\bclass\b"],
    "reasoning": [r"\bsolve\b", r"\bprove\b", r"\banalyze\b", r"\bstep by step\b"],
    "summarization": [r"\bsummariz", r"\btl;?dr\b", r"\bcondense\b", r"\bshorten\b"],
}
```

### Fallback & Circuit Breaker

#### Simplified Fallback Chains
Each model has **max 2 backup models** for fast recovery:

```
llama-3.3-70b-versatile → moonshotai/kimi-dev-72b:free
deepseek-r1-distill-llama-70b → llama-3.3-70b-versatile
llama-3.1-8b-instant → deepseek-r1-distill-llama-70b
mixtral-8x7b-32k → llama-3.3-70b-versatile
```

#### Circuit Breaker Pattern
Prevents cascading failures by tracking model health:

```
┌─────────────────────────────────────────────────────────────┐
│                   CIRCUIT BREAKER STATES                    │
├─────────────────────────────────────────────────────────────┤
│ CLOSED    → Normal operation, requests allowed              │
│ OPEN      → Model blocked after 5 failures (60s cooldown)   │
│ HALF_OPEN → Testing with single request after cooldown      │
└─────────────────────────────────────────────────────────────┘
```

Configuration:
- `CIRCUIT_BREAK_THRESHOLD`: Number of failures before opening (default: 5)
- `CIRCUIT_BREAK_RESET_SECONDS`: Cooldown period (default: 60)

---

## Memory System Architecture

### Layered Memory Design

Kuro uses a **3-layer progressive memory system** to maintain conversation context efficiently:

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY LAYERS                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LAYER 1: SHORT-TERM (Raw Messages)                  │   │
│  │ • Last 20 message exchanges (user + assistant)      │   │
│  │ • Full fidelity, no compression                     │   │
│  │ • Stored in MongoDB chat_collection                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LAYER 2: MEDIUM-TERM (Summarized Batches)           │   │
│  │ • Batches of 8+ messages → single summary           │   │
│  │ • Content-hashed to avoid re-summarization          │   │
│  │ • Stored in conversation_summaries collection       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LAYER 3: LONG-TERM (Vector Embeddings + Facts)      │   │
│  │ • Semantic search via Pinecone                      │   │
│  │ • Verbatim facts (immutable, high importance)       │   │
│  │ • Cross-session memory recall                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Vector Storage (Pinecone)

**Configuration:**
- **Index Name**: `my-chatbot-memory` (configurable via `PINECONE_INDEX_NAME`)
- **Dimensions**: 384 (downsampled from Gemini's 768)
- **Embedding Model**: Google Gemini `text-embedding-004`

**Memory Document Schema:**
```python
{
    "id": "uuid",
    "text": "Actual memory content",
    "embedding": [0.1, 0.2, ...],  # 384-dim vector
    "metadata": {
        "user": "user_id",
        "timestamp": "ISO8601",
        "importance": 0.5,  # 0.0-1.0 scale
        "category": "summary|fact|general",
        "session_id": "session_uuid",
        "type": "long_term_summary|layered_summary|verbatim_fact"
    }
}
```

**Importance Scores:**
- `0.95` - Verbatim facts (user preferences, names, explicit statements)
- `0.90` - Layered summaries (structured conversation summaries)
- `0.85` - Standard summaries (compressed conversation batches)
- `0.50` - General memories (default)

### Progressive Summarization

The `RollingMemoryManager` (`rolling_memory.py`) handles automatic memory compression:

```
┌─────────────────────────────────────────────────────────────┐
│              SUMMARIZATION WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. TRIGGER: Total messages > (short_term_window + 8)      │
│     └─> Currently: 20 + 8 = 28 messages                    │
│                                                             │
│  2. CHUNK SELECTION:                                        │
│     └─> Messages (last_summarized + 1) to (total - 20)     │
│     └─> Minimum chunk size: 8 messages                     │
│                                                             │
│  3. HASH CHECK:                                             │
│     └─> SHA-256 of block_text                              │
│     └─> Skip if identical hash already exists              │
│                                                             │
│  4. DUAL SUMMARIZATION:                                     │
│     └─> Standard summary (legacy format)                   │
│     └─> Layered summary (structured extraction)            │
│                                                             │
│  5. FACT EXTRACTION:                                        │
│     └─> Extract verbatim facts from layered summary        │
│     └─> Lines starting with '-' under FACTS sections       │
│                                                             │
│  6. STORAGE:                                                │
│     └─> MongoDB: conversation_summaries                    │
│     └─> Pinecone: Vectorized for semantic search           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Summarization Prompts** (`summarization_prompts.py`, `layered_summarization_prompts.py`):
- **Standard**: Extracts key topics, decisions, user preferences
- **Layered**: Structured format with FACTS, TOPICS, DECISIONS, OTHER_NOTES sections

### Context Rehydration

The `build_context()` function (`context_rehydrator.py`) assembles conversation context for each query:

```python
# Assembly Priority (highest to lowest):
1. FACTS       → Immutable verbatim user facts (never trimmed)
2. SUMMARIES   → Layered conversation summaries (oldest trimmed first)
3. RECENT_TURNS → Last N raw exchanges (trimmed if over budget)
```

**Token Budget Management:**
- Default max: 2000 tokens
- When over budget: Drop oldest summaries first
- Facts are **never** removed from context

**Output Format:**
```
FACTS:
- User's name is John
- User prefers Python over JavaScript

SUMMARIES:
---
Previous session discussed machine learning projects...
---
User asked about deployment strategies...

RECENT_TURNS:
User: How do I fix this error?
Assistant: Let me help you debug that...
```

---

## Orchestration Flow

The `llm_orchestrator.py` manages the complete execution pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  USER MESSAGE                                               │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐                                   │
│  │ Intent Classification │ ← classify_intent()             │
│  │ (Regex-based, fast)   │                                 │
│  └──────────┬────────────┘                                 │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────┐                                   │
│  │ Skill Injection      │ ← skill_manager.build_injected() │
│  │ (System prompt mods) │                                  │
│  └──────────┬────────────┘                                 │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────┐                                   │
│  │ Context Assembly     │ ← RAG + Memory context           │
│  │ (Token budgeting)    │                                  │
│  └──────────┬────────────┘                                 │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────┐                                   │
│  │ Model Routing        │ ← get_best_model_v2()            │
│  │ (Skill-based)        │                                  │
│  └──────────┬────────────┘                                 │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────┐                                   │
│  │ Circuit Breaker      │ ← Check model health             │
│  │ (Failure prevention) │                                  │
│  └──────────┬────────────┘                                 │
│             │                                               │
│             ▼                                               │
│  ┌─────────────────────┐                                   │
│  │ LLM Execution        │ ← GroqClient / OpenRouterClient  │
│  │ (With retry logic)   │                                  │
│  └──────────┬────────────┘                                 │
│             │                                               │
│        ┌────┴────┐                                         │
│        │ Success │                                         │
│        │    ?    │                                         │
│        └────┬────┘                                         │
│         No  │  Yes                                         │
│         │   │                                              │
│         ▼   ▼                                              │
│    ┌────────────┐   ┌───────────────┐                     │
│    │ Fallback   │   │ Record Success│                     │
│    │ Chain      │   │ Return Reply  │                     │
│    └────────────┘   └───────────────┘                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Retry Logic:**
- Transient errors (timeout, 429, rate limit): Retry up to 2x with exponential backoff
- Non-transient errors: Immediate fallback to next model in chain

---

## External Services

### Groq (Primary Provider)
- **Endpoint**: `api.groq.com`
- **Models**: LLaMA 3.1/3.3, DeepSeek R1, Mixtral, Gemma
- **Advantages**: Fastest inference (~200-800ms), free tier available
- **Client**: `utils/groq_client.py`

### OpenRouter (Fallback Provider)
- **Endpoint**: `openrouter.ai/api`
- **Models**: GPT-4, Claude, Gemini, and 100+ others
- **Advantages**: Model diversity, premium model access
- **Client**: `utils/openrouter_client.py`

### Pinecone (Vector Database)
- **Purpose**: Semantic memory storage and retrieval
- **Index**: Single index per deployment
- **Queries**: Cosine similarity search with user filtering

### MongoDB (Document Database)
- **Collections**:
  - `chat_messages` - Raw chat history
  - `conversation_summaries` - Compressed memory batches
  - `sessions` - User session metadata
  - `user_profiles` - User preferences and names

### Google Gemini (Embeddings Only)
- **Model**: `text-embedding-004`
- **Purpose**: Generate 768-dim vectors (downsampled to 384 for Pinecone)
- **Cost**: Free tier sufficient for most usage

---

## Configuration Reference

### Environment Variables

```bash
# === AI Providers ===
GROQ_API_KEY=gsk_...                    # Groq API key (required)
OPENROUTER_API_KEY=sk-or-...            # OpenRouter API key (optional fallback)

# === Embeddings & Vector Store ===
GEMINI_API_KEY=...                       # Google Gemini for embeddings
PINECONE_API_KEY=...                     # Pinecone vector database
PINECONE_INDEX_NAME=my-chatbot-memory    # Index name (default)

# === Database ===
MONGODB_URI=mongodb+srv://...            # MongoDB connection string

# === Routing Strategy ===
ROUTING_STRATEGY=skill                   # "skill" (default) or "score"
ENABLE_SCORE_ROUTING=false               # Enable experimental scoring

# === Circuit Breaker ===
CIRCUIT_BREAK_THRESHOLD=5                # Failures before opening
CIRCUIT_BREAK_RESET_SECONDS=60           # Cooldown period

# === Memory System ===
DISABLE_MEMORY_INIT=0                    # Set to 1 for testing
RAG_INDEX_CHECK_INTERVAL=300             # Seconds between index checks

# === Debug ===
LOG_RAW_CONTENT=false                    # Verbose routing logs
```

### Model Registry (`config/model_registry.yml`)

```yaml
models:
  - id: model-id
    label: friendly_name
    capabilities: [list, of, capabilities]
    fallback: ["backup-model-1", "backup-model-2"]
    max_context_tokens: 16384
    avg_latency_ms: 1000
    quality_tier: high|medium|low
    cost_score: 1-5  # 1=cheapest, 5=most expensive

routing_rules:
  - name: rule_name
    intent: "intent_name"        # OR
    condition: "expression"      # e.g., "context_tokens > 20000"
    choose: "model-id"
```

---

## Summary

Kuro AI implements a sophisticated but maintainable architecture:

1. **4 Specialized Models** - One model per skill (conversation, reasoning, code, summarization)
2. **Rule-Based Routing** - Fast, deterministic model selection via intent/keyword patterns
3. **3-Layer Memory** - Short-term raw, medium-term summaries, long-term vectors
4. **Progressive Summarization** - Automatic compression as conversations grow
5. **Circuit Breakers** - Automatic failure recovery with fallback chains
6. **Vector Search** - Semantic memory recall across sessions

This design prioritizes **speed** (Groq inference), **reliability** (fallback chains), and **cost-efficiency** (free-tier models) while maintaining high response quality.
