# Kuro AI: Model Routing & Skill Selection Logic

## 🎯 **Complete Request Flow: How Kuro AI Routes Models and Selects Skills**

### **📋 Overview of the System**
Kuro AI uses two parallel systems that work together:
1. **Model Routing System** - Chooses which AI model to use
2. **Skill Selection System** - Injects specialized behavior prompts

---

## 🚀 **Step 1: Intent Classification**

**File**: `backend/routing/intent_classifier.py`

When a user sends a message, the system first classifies the intent using keyword patterns:

```python
# Example intents:
- "casual_chat" (default fallback)  
- "long_context_summary" (keywords: summarize, condense, tl;dr)
- "complex_reasoning" (keywords: prove, derive, step by step)  
- "tool_use_or_function_call" (keywords: call api, invoke function)
- "high_creativity_generation" (keywords: story, poem, creative)
```

**Logic**:
1. **Developer Override**: If `developer_override` parameter is set, use that intent
2. **Inline Force**: If message contains "INTENT:xyz", extract and use "xyz"
3. **Pattern Matching**: Scan message for regex patterns, add matching intents
4. **Default Fallback**: If no patterns match, default to "casual_chat"

---

## 🎯 **Step 2: Model Selection (3-Tier Routing)**

**Files**: `backend/routing/model_router.py` + `backend/config/model_registry.yml`

The model router has **3 selection strategies** in order of priority:

### **Tier 1: Forced Model Override**
```python
if forced_model:
    return {"model_id": forced_model, "rule": "forced_override"}
```

### **Tier 2: Rule-Based Selection**
**Intent Rules**: Match exact intent to specific model
```yaml
- name: casual_greeting
  intent: "casual_chat" 
  choose: "llama-3.1-8b-instant"

- name: reasoning_tasks  
  intent: "math_solver"
  choose: "deepseek-r1-distill-llama-70b"
```

**Condition Rules**: Evaluate expressions based on message metrics
```yaml
- name: long_document
  condition: "context_tokens > 20000"
  choose: "mixtral-8x7b-32k"

- name: short_query  
  condition: "context_tokens < 2000 and message_len_chars < 300"
  choose: "llama-3.1-8b-instant"
```

### **Tier 3: Score-Based Selection** 
If no rules match, the system **scores all models** based on:

```python
def _score_model(model, intents, context_tokens):
    score = 0.0
    
    # +5 points for capability matches
    if intent_matches_capability(intent, model.capabilities):
        score += 5
    
    # -10 points if context exceeds model limit  
    if context_tokens > model.max_context_tokens:
        score -= 10
        
    # Latency bonus for casual chat
    if "casual_chat" in intents:
        score += (1000 - model.avg_latency_ms) / 1000
        
    # Quality bonus for complex tasks
    if model.quality_tier == "high":
        score += 3
        
    # Cost penalty for simple tasks
    if intents == {"casual_chat"}:
        score -= model.cost_score * 0.2
```

**Example Scoring**:
- User: "hey there" (casual_chat, 50 chars, 12 tokens)
- `llama-3.1-8b-instant`: +5 (capability) +0.65 (latency) -0.2 (cost) = **5.45**
- `llama-3.3-70b-versatile`: +5 (capability) +0.1 (latency) -0.6 (cost) = **4.5**
- **Winner**: `llama-3.1-8b-instant` (faster, cheaper for casual chat)

---

## 🎨 **Step 3: Skill Selection (Pattern-Based System)**

**Files**: `backend/skills/skill_manager.py` + `backend/skills/skills.json`

Skills work **independently** from model routing. They inject specialized system prompts.

### **Skill Detection Process**:

1. **Pattern Matching**: Each skill has trigger patterns (regex + keywords)
```json
{
  "name": "math_solver",
  "trigger_patterns": ["solve", "equation", "calculate", "algebra"],
  "system_prompt": "You are in MATH mode. Provide step-by-step solutions..."
}
```

2. **Scoring**: For each skill, count pattern matches
```python
def skill.match(user_text):
    score = 0
    for pattern in trigger_patterns:
        if pattern.search(user_text.lower()):
            score += 1  # +1 for each match
    for negative_pattern in negative_patterns:  
        if negative_pattern.search(user_text.lower()):
            score -= 1  # -1 for exclusions
    return score
```

3. **Filtering & Ranking**:
   - **Minimum Score**: Skills need score ≥ 1 to activate
   - **Cooldown**: Skip if skill used recently (prevents spam)
   - **Priority Sort**: Sort by `(priority desc, score desc)`
   - **Chaining**: Select up to 3 skills (if `allow_chain=true`)

4. **System Prompt Injection**:
```python
# Base system prompt + skill injections
final_prompt = base_system + "\n\n" + skill1.system_prompt + "\n\n" + skill2.system_prompt
```

### **Example Skill Selection**:
User: **"Can you solve this equation: x^2 + 5x + 6 = 0"**

**Pattern Matches**:
- `math_solver`: "solve" + "equation" = **score 2** ✅
- `teaching`: "can you" = **score 1** ✅  
- `casual_chat`: No matches = **score 0** ❌

**Selected Skills** (priority order):
1. `math_solver` (priority 6, score 2) 
2. `teaching` (priority 5, score 1)

**Final System Prompt**:
```
[Base Kuro system prompt]

[SKILL:MATH_SOLVER|cat=math|prio=6]
You are in MATH mode. Provide step-by-step solutions...

[SKILL:TEACHING|cat=education|prio=5]  
You are in TEACHING mode. Structure: (1) Simple definition...
```

---

## 🔄 **Step 4: Fallback & Error Handling**

### **Model Fallback Chain**:
If the selected model fails (rate limit, error), the system tries backup models:

```yaml
llama-3.1-8b-instant:
  fallback: ["llama-3.3-70b-versatile", "meta-llama/llama-3.3-8b-instruct:free"]
```

**Process**:
1. Primary model fails → Circuit breaker records failure
2. `choose_fallback(failed_model)` → Returns next model in chain
3. Retry with backup model → Continue until success or exhausted
4. If all models fail → Return user-friendly error message

### **Provider Routing (Groq vs OpenRouter)**:
**File**: `backend/orchestration/llm_orchestrator.py`

The system automatically chooses between Groq and OpenRouter:
```python
MODEL_SOURCES = {
    "llama-3.1-8b-instant": "Groq",
    "meta-llama/llama-3.3-8b-instruct:free": "OpenRouter",
    "deepseek-r1-distill-llama-70b": "Groq",
    # ... etc
}

# Route to appropriate provider
if model_source == "Groq":
    return groq_client.generate_content(...)
elif model_source == "OpenRouter":  
    return openrouter_client.generate_content(...)
```

---

## 📊 **Complete Example: Request Processing**

**User Input**: *"Hey! Can you summarize this long article I pasted..."*

### **Step 1: Intent Classification**
- Pattern: "summarize" → **Intent: "long_context_summary"**

### **Step 2: Model Selection** 
- Rule match: None (no exact intent rules)
- Condition check: `context_tokens = 25000 > 20000` → **Rule: "long_document"**
- **Selected Model**: `mixtral-8x7b-32k` (32k context limit)

### **Step 3: Skill Selection**
- `summarizing`: "summarize" = **score 1** ✅ (priority 5)
- `casual_chat`: "hey" = **score 1** ✅ (priority 8) 
- **Selected Skills**: `casual_chat` + `summarizing`

### **Step 4: Final Request**
- **Model**: `mixtral-8x7b-32k` via Groq
- **System Prompt**: Base + casual_chat injection + summarizing injection
- **Fallbacks**: `mistralai/mistral-small-3.2-24b-instruct:free` → `z-ai/glm-4.5-air:free`

### **Result**: 
Fast, friendly greeting + structured article summarization with long-context model.

---

## 🔧 **Current Model Configuration**

### **Fast Chat Models** (Low-latency, casual use)
| Model | Provider | Context | Avg Latency | Use Case |
|-------|----------|---------|-------------|----------|
| `llama-3.1-8b-instant` | Groq | 8k | 350ms | Quick responses, greetings |
| `meta-llama/llama-3.3-8b-instruct:free` | OpenRouter | 8k | 400ms | Fast chat backup |

### **High-Quality Reasoning Models** (Complex problems)
| Model | Provider | Context | Avg Latency | Use Case |
|-------|----------|---------|-------------|----------|
| `deepseek-r1-distill-llama-70b` | Groq | 16k | 1200ms | Math, logic, analysis |
| `deepseek/deepseek-r1:free` | OpenRouter | 16k | 1400ms | Advanced reasoning |
| `qwen/qwen3-30b-a3b:free` | OpenRouter | 16k | 1000ms | Strong reasoning backup |

### **Long-Context Models** (Document processing)
| Model | Provider | Context | Avg Latency | Use Case |
|-------|----------|---------|-------------|----------|
| `mixtral-8x7b-32k` | Groq | 32k | 1100ms | Long documents |
| `mistralai/mistral-small-3.2-24b-instruct:free` | OpenRouter | 131k | 1300ms | Very long content |
| `z-ai/glm-4.5-air:free` | OpenRouter | 131k | 1200ms | Long context backup |

### **Balanced General Models** (Versatile use)
| Model | Provider | Context | Avg Latency | Use Case |
|-------|----------|---------|-------------|----------|
| `llama-3.3-70b-versatile` | Groq | 8k | 900ms | General queries |
| `meta-llama/llama-3.3-70b-instruct:free` | OpenRouter | 8k | 1000ms | General backup |
| `moonshotai/kimi-dev-72b:free` | OpenRouter | 131k | 1100ms | Creative + long context |

---

## 🎯 **Current Skills Configuration**

### **Priority 8** (Highest - Always first)
- **`casual_chat`**: Handles greetings ("hey", "hello", "how are you")

### **Priority 7** (High priority)
- **`fact_check`**: Verifies information ("is it true", "verify", "fact check")
- **`clarifier`**: Asks clarifying questions ("help", "unclear", "confused")

### **Priority 6** (Important tasks)
- **`debugging`**: Fixes copy-pasted errors ("error", "exception", "stack trace")
- **`math_solver`**: Solves math problems ("solve", "equation", "calculate")

### **Priority 5** (Core functionality)
- **`summarizing`**: Structured text summarization ("summarize", "tl;dr")
- **`teaching`**: Explains concepts clearly ("explain", "teach", "how does")
- **`translation`**: Language translation ("translate", "in spanish")

### **Priority 4** (Creative & communication)
- **`brainstorming`**: Generates ideas ("ideas", "brainstorm", "suggestions")
- **`storytelling`**: Creates narratives ("story", "narrative", "creative writing")
- **`rewrite_tone`**: Improves text style ("rewrite", "improve", "make it")

---

## ⚙️ **Configuration Points**

### **Environment Variables**
```bash
SKILL_MIN_SCORE=1              # Minimum score for skill activation
SKILL_MAX_CHAIN=3              # Maximum skills per request  
SKILL_DEBUG=1                  # Enable detailed skill matching logs
CIRCUIT_BREAK_RESET_SECONDS=60 # Circuit breaker reset time
```

### **Key Configuration Files**
- `backend/config/model_registry.yml` - Models + routing rules
- `backend/skills/skills.json` - Skill definitions + patterns
- `backend/utils/groq_client.py` - Groq model mappings
- `backend/utils/openrouter_client.py` - OpenRouter model mappings
- `backend/config/kuro_system_prompt.txt` - Base system prompt

### **Routing Rules (Current)**
```yaml
# Casual greetings → Fast model
- name: casual_greeting
  intent: "casual_chat"
  choose: "llama-3.1-8b-instant"

# Long documents → High context model  
- name: long_document
  condition: "context_tokens > 20000"
  choose: "mixtral-8x7b-32k"

# Math problems → Reasoning model
- name: reasoning_tasks
  intent: "math_solver"
  choose: "deepseek-r1-distill-llama-70b"

# Short queries → Fast model
- name: short_query
  condition: "context_tokens < 2000 and message_len_chars < 300"
  choose: "llama-3.1-8b-instant"

# Default → Balanced model
- name: default
  choose: "llama-3.3-70b-versatile"
```

---

## 🔍 **Debugging & Monitoring**

### **Logs to Watch**
```bash
# Model selection
"Groq routed model=llama-3.1-8b-instant rule=short_query attempt=1"

# Skill application  
"Applied skills: ['casual_chat', 'math_solver']"

# Fallback usage
"Circuit breaker for llama-3.1-8b-instant: failure 1/5"
"choose_fallback(llama-3.1-8b-instant) -> llama-3.3-70b-versatile"
```

### **Performance Metrics**
```bash
# Request completion
"llm_request_complete latency_ms=850 request_id=abc123 status=200"

# Provider routing
"openrouter_call provider=OpenRouter model_slug=meta-llama/llama-3.3-8b-instruct:free latency_ms=1200"
```

This dual-system approach ensures Kuro AI can **intelligently route to optimal models** while **injecting appropriate behavioral expertise** for each type of user request! 🎯
