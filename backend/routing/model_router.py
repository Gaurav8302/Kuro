"""Model router (Step 4) evaluates routing rules and selects a model.

Exposed function: route_model(message: str, context_tokens: int, intent: str | None) -> dict
Returns: { 'model_id': str, 'rule': str }
"""
from __future__ import annotations
import re
from typing import Optional, Dict, Any
from config.config_loader import get_routing_rules, list_models, get_model
from typing import Set

SAFE_DEFAULT = "llama-3.3-70B-versatile"

# Simple expression evaluator for rule condition subset
_allowed_names = {"context_tokens", "message_len_chars"}

def _eval_condition(expr: str, vars: Dict[str, Any]) -> bool:
    try:
        # Disallow builtins by passing empty dicts
        return bool(eval(expr, {"__builtins__": {}}, vars))
    except Exception:
        return False

_intent_pattern_cache = {}


def _score_model(m: Dict[str,Any], intents: Set[str], context_tokens: int) -> float:
    score = 0.0
    caps = set(m.get("capabilities", []))
    # Intent to capability mapping
    mapping = {
        "casual_chat": "general",
        "long_context_summary": "long_context",
        "complex_reasoning": "reasoning",
        "tool_use_or_function_call": "tool_use",
        "high_creativity_generation": "high_quality",
    }
    for intent in intents:
        cap = mapping.get(intent)
        if cap and cap in caps:
            score += 5
    # penalize if context too small
    max_ctx = int(m.get("max_context_tokens", 0) or 0)
    if max_ctx < context_tokens:
        score -= 10
    # latency preference: add inverse latency weight for casual & fast
    if "casual_chat" in intents and m.get("avg_latency_ms"):
        score += max(0, 1000 - int(m["avg_latency_ms"])) / 1000
    # quality preference
    if any(i in intents for i in ("complex_reasoning","high_creativity_generation")):
        tier = m.get("quality_tier")
        if tier == "high":
            score += 3
        elif tier == "medium":
            score += 1
    # cost penalty when casual only
    if intents == {"casual_chat"}:
        score -= float(m.get("cost_score", 1))*0.2
    return score

def route_model(message: str, context_tokens: int, intents: Optional[Set[str]] = None, forced_model: Optional[str] = None, intent: Optional[str] = None) -> Dict[str, Any]:
    # Back-compat: some callers pass 'intent' singular; merge into intents set
    if intent and not intents:
        intents = {intent}
    # Forced override
    if forced_model and get_model(forced_model):
        return {"model_id": forced_model, "rule": "forced_override"}

    first_intent = None
    if intents:
        sorted_intents = sorted(intents)
        first_intent = sorted_intents[0]
    vars = {"context_tokens": context_tokens, "message_len_chars": len(message)}
    rules = get_routing_rules()
    for rule in rules:
        r_intent = rule.get("intent")
        if r_intent and first_intent and r_intent == first_intent:
            return {"model_id": rule.get("choose", SAFE_DEFAULT), "rule": rule.get("name", "intent_match")}
        cond = rule.get("condition")
        if cond and _eval_condition(cond, vars):
            return {"model_id": rule.get("choose", SAFE_DEFAULT), "rule": rule.get("name", "condition_match")}
    # Score based selection
    models = list_models()
    if not models:
        return {"model_id": SAFE_DEFAULT, "rule": "unavailable_registry"}
    best = None
    best_score = -1e9
    for m in models:
        s = _score_model(m, intents or {"casual_chat"}, context_tokens)
        if s > best_score:
            best = m
            best_score = s
    if best:
        return {"model_id": best["id"], "rule": "scored_selection", "score": best_score}
    return {"model_id": SAFE_DEFAULT, "rule": "final_default"}

__all__ = ["route_model"]
