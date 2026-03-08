"""Model Router v3 — LLM-based classifier with research pipeline.

Execution order:
  1. Forced override (if provided)
  2. Cache check (128-char key, 300s TTL)
  3. Router classifier (LLM call via llama-3.1-8b-instant)
  4. Research decision (router output or manual search_mode)
  5. Compound research (optional, via groq/compound-mini)
  6. Final model execution (selected model + research context + memory)

The router NEVER generates user-facing answers. It only returns routing
decisions as structured JSON.

Exports:
  - get_best_model(query, session_id, forced_model, search_mode)
  - run_router_classifier(query)
  - needs_research(query, router_output)
  - execute_final_model(query, model, memory_context, research_context)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

from routing import router_cache
from routing.compound_research import run_compound_research
from routing.routing_logger import log_routing_decision as _log_decision

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model constants (matching the spec)
# ---------------------------------------------------------------------------
CONVERSATION_MODEL = "llama-3.1-8b-instant"
REASONING_MODEL = "deepseek-r1-distill-llama-70b"
CODE_MODEL = "llama-3.1-8b-instant"
SUMMARIZATION_MODEL = "mixtral-8x7b-32k"
RESEARCH_SYSTEM = "groq/compound-mini"

# The lightweight model used for the router classifier itself
_ROUTER_MODEL = "llama-3.1-8b-instant"

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ---------------------------------------------------------------------------
# Model map: task_type + complexity → final model
# ---------------------------------------------------------------------------
_MODEL_SELECTION: Dict[str, str] = {
    "conversation:simple": CONVERSATION_MODEL,
    "conversation:moderate": CONVERSATION_MODEL,
    "conversation:complex": CONVERSATION_MODEL,
    "code:simple": CODE_MODEL,
    "code:moderate": CODE_MODEL,
    "code:complex": CODE_MODEL,
    "summarization:simple": SUMMARIZATION_MODEL,
    "summarization:moderate": SUMMARIZATION_MODEL,
    "summarization:complex": SUMMARIZATION_MODEL,
    "reasoning:simple": CONVERSATION_MODEL,
    "reasoning:moderate": CONVERSATION_MODEL,
    "reasoning:complex": REASONING_MODEL,
    "research:simple": REASONING_MODEL,
    "research:moderate": REASONING_MODEL,
    "research:complex": REASONING_MODEL,
}

# ---------------------------------------------------------------------------
# Router system prompt (spec-defined, never generates user answers)
# ---------------------------------------------------------------------------
_ROUTER_SYSTEM_PROMPT = """You are the routing engine for an AI assistant called Kuro.
Your job is to analyze the user query and decide the optimal execution plan before any model generates the final response.

You must determine:
1. task type
2. complexity level
3. whether external research is required
4. which model should generate the final response

You do NOT answer the user question.

---

AVAILABLE MODELS

conversation_model
* llama-3.1-8b-instant (Groq)

reasoning_model
* deepseek-r1-distill-llama-70b (Groq)

code_model
* llama-3.1-8b-instant (Groq)

summarization_model
* mixtral-8x7b-32k (Groq)

research_system
* groq/compound-mini

---

TASK TYPES

conversation — casual chat, greetings, simple explanations
reasoning — logical analysis, math, comparisons, analytical thinking
code — any programming request
summarization — summarizing text or conversation history
research — questions requiring real-time information

---

RESEARCH TRIGGERS

Research is required when the question involves:
- recent events
- news
- statistics
- financial comparisons
- market data
- technology releases
- information likely to change frequently

---

COMPLEXITY LEVELS: simple, moderate, complex

---

MODEL SELECTION RULES

conversation + simple → conversation_model
conversation + moderate → conversation_model
code → code_model
summarization → summarization_model
reasoning + moderate → conversation_model
reasoning + complex → reasoning_model
If research_required is true → final_model must be reasoning_model

---

OUTPUT FORMAT

Return ONLY valid JSON:

{"task_type": "", "complexity": "", "research_required": false, "research_system": "", "final_model": "", "confidence": 0.0, "reason": ""}"""


# ---------------------------------------------------------------------------
# run_router_classifier
# ---------------------------------------------------------------------------
def run_router_classifier(query: str) -> Dict[str, Any]:
    """Call the LLM router classifier to get a routing decision.

    Returns a dict with keys: task_type, complexity, research_required,
    research_system, final_model, confidence, reason.
    Falls back to a safe default on any failure.
    """
    default = {
        "task_type": "conversation",
        "complexity": "simple",
        "research_required": False,
        "research_system": "",
        "final_model": CONVERSATION_MODEL,
        "confidence": 0.5,
        "reason": "classifier_fallback",
    }

    if not _GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — using default routing")
        return default

    try:
        payload = {
            "model": _ROUTER_MODEL,
            "messages": [
                {"role": "system", "content": _ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "temperature": 0.0,
            "max_tokens": 256,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {_GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        start = time.time()
        resp = requests.post(
            f"{_GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=10,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info("Router classifier responded in %dms", elapsed_ms)

        if resp.status_code != 200:
            logger.warning("Router classifier HTTP %d", resp.status_code)
            return default

        raw_content = (
            resp.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        # Parse JSON from the response (handle markdown code fences)
        json_str = raw_content
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_content, re.S)
        if fence_match:
            json_str = fence_match.group(1).strip()

        parsed = json.loads(json_str)

        # Validate and normalise
        task_type = parsed.get("task_type", "conversation")
        if task_type not in ("conversation", "reasoning", "code", "summarization", "research"):
            task_type = "conversation"

        complexity = parsed.get("complexity", "simple")
        if complexity not in ("simple", "moderate", "complex"):
            complexity = "simple"

        research_required = bool(parsed.get("research_required", False))

        # Enforce model selection rules
        key = f"{task_type}:{complexity}"
        final_model = _MODEL_SELECTION.get(key, CONVERSATION_MODEL)
        if research_required:
            final_model = REASONING_MODEL

        confidence = float(parsed.get("confidence", 0.8))
        confidence = max(0.0, min(1.0, confidence))

        return {
            "task_type": task_type,
            "complexity": complexity,
            "research_required": research_required,
            "research_system": RESEARCH_SYSTEM if research_required else "",
            "final_model": final_model,
            "confidence": confidence,
            "reason": parsed.get("reason", ""),
        }

    except json.JSONDecodeError:
        logger.warning("Router classifier returned invalid JSON")
        return default
    except Exception as e:
        logger.error("Router classifier failed: %s", e)
        return default


# ---------------------------------------------------------------------------
# needs_research
# ---------------------------------------------------------------------------
def needs_research(query: str, router_output: Dict[str, Any]) -> bool:
    """Determine whether research is needed based on router output."""
    return bool(router_output.get("research_required", False))


# ---------------------------------------------------------------------------
# execute_final_model
# ---------------------------------------------------------------------------
def execute_final_model(
    query: str,
    model: str,
    memory_context: Optional[str] = None,
    research_context: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Optional[str]:
    """Call the final model with query, optional research context, and memory.

    When research_context is provided the prompt is structured per spec:
      User Question → Research Context → Conversation Memory → Instructions
    """
    if not _GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set — cannot execute final model")
        return None

    # Build the user prompt
    parts: List[str] = []
    parts.append(f"User Question:\n{query}")

    if research_context:
        parts.append(f"Research Context:\n{research_context}")

    if memory_context:
        parts.append(f"Conversation Memory:\n{memory_context}")

    if research_context:
        parts.append(
            "Instructions:\n"
            "Use the research information if relevant. "
            "Combine it with the conversation context to produce a clear answer."
        )

    user_content = "\n\n".join(parts)

    # Map model IDs to Groq API names
    groq_model_map = {
        "llama-3.1-8b-instant": "llama-3.1-8b-instant",
        "deepseek-r1-distill-llama-70b": "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32k": "mixtral-8x7b-32768",
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
    }
    groq_model = groq_model_map.get(model, model)

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    try:
        payload = {
            "model": groq_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {_GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{_GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning("Final model HTTP %d: %s", resp.status_code, resp.text[:300])
            return None

        content = (
            resp.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return content or None

    except Exception as e:
        logger.error("Final model execution failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# get_best_model — main entry point
# ---------------------------------------------------------------------------
def get_best_model(
    query: str,
    session_id: Optional[str] = None,
    forced_model: Optional[str] = None,
    search_mode: bool = False,
) -> Dict[str, Any]:
    """Smart routing pipeline — returns a routing decision dict.

    Pipeline:
      1. Forced override → immediate return
      2. Cache check → return if fresh
      3. LLM classifier → routing decision
      4. Override research_required if search_mode is True

    Returns dict with keys:
      chosen_model, task_type, complexity, research_required,
      confidence, reason, source
    """
    start = time.time()

    # --- 1. Forced override ---
    if forced_model:
        decision = {
            "chosen_model": forced_model,
            "task_type": "forced",
            "complexity": "n/a",
            "research_required": search_mode,
            "confidence": 1.0,
            "reason": "forced_override",
            "source": "override",
        }
        elapsed = int((time.time() - start) * 1000)
        _log_decision(
            query=query,
            chosen_model=forced_model,
            task_type="forced",
            complexity="n/a",
            research_required=search_mode,
            confidence=1.0,
            latency_ms=elapsed,
            fallback_used=False,
        )
        return decision

    # --- 2. Cache check ---
    cached = router_cache.get(query)
    if cached and not search_mode:
        # Return cached decision (strip internal timestamp)
        result = {k: v for k, v in cached.items() if k != "_ts"}
        elapsed = int((time.time() - start) * 1000)
        _log_decision(
            query=query,
            chosen_model=result.get("chosen_model", CONVERSATION_MODEL),
            task_type=result.get("task_type", "conversation"),
            complexity=result.get("complexity", "simple"),
            research_required=result.get("research_required", False),
            confidence=result.get("confidence", 0.95),
            latency_ms=elapsed,
            extra={"cache_hit": True},
        )
        return result

    # --- 3. LLM classifier ---
    router_output = run_router_classifier(query)

    # --- 4. Search mode override ---
    if search_mode:
        router_output["research_required"] = True
        router_output["research_system"] = RESEARCH_SYSTEM
        router_output["final_model"] = REASONING_MODEL

    decision = {
        "chosen_model": router_output["final_model"],
        "task_type": router_output["task_type"],
        "complexity": router_output["complexity"],
        "research_required": router_output["research_required"],
        "confidence": router_output["confidence"],
        "reason": router_output["reason"],
        "source": "router_v3",
    }

    # Cache the decision
    router_cache.put(query, decision)

    elapsed = int((time.time() - start) * 1000)
    _log_decision(
        query=query,
        chosen_model=decision["chosen_model"],
        task_type=decision["task_type"],
        complexity=decision["complexity"],
        research_required=decision["research_required"],
        confidence=decision["confidence"],
        latency_ms=elapsed,
    )

    logger.info(
        "Router v3 decision: model=%s type=%s complexity=%s research=%s conf=%.2f (%dms)",
        decision["chosen_model"],
        decision["task_type"],
        decision["complexity"],
        decision["research_required"],
        decision["confidence"],
        elapsed,
    )

    return decision


__all__ = [
    "get_best_model",
    "run_router_classifier",
    "needs_research",
    "run_compound_research",
    "execute_final_model",
    "CONVERSATION_MODEL",
    "REASONING_MODEL",
    "CODE_MODEL",
    "SUMMARIZATION_MODEL",
]
