"""Model router (Step 4) evaluates routing rules and selects a model.

Exposed function: route_model(message: str, context_tokens: int, intent: str | None) -> dict
Returns: { 'model_id': str, 'rule': str }
"""
from __future__ import annotations
import re
import logging
from typing import Optional, Dict, Any
from config.config_loader import get_routing_rules, list_models, get_model
from config.model_config import normalize_model_id
from typing import Set

logger = logging.getLogger(__name__)

SAFE_DEFAULT = normalize_model_id("llama-3.3-70B-versatile")

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
    
    # Forced override with normalization and validation
    if forced_model:
        forced_norm = normalize_model_id(forced_model)
        if forced_norm != forced_model:
            logger.debug("Normalized forced_model %s -> %s", forced_model, forced_norm)
        try:
            model_config = get_model(forced_norm)
            if model_config:
                logger.debug("Using forced model: %s", forced_norm)
                return {"model_id": forced_norm, "rule": "forced_override"}
            else:
                logger.warning("Forced model %s not found in registry, falling back to routing", forced_norm)
        except Exception as e:
            logger.warning("Error validating forced model %s: %s, falling back to routing", forced_norm, str(e))

    # Rule evaluation with error handling
    first_intent = None
    if intents:
        sorted_intents = sorted(intents)
        first_intent = sorted_intents[0]
        logger.debug("Processing intents: %s (primary: %s)", sorted_intents, first_intent)
    
    vars = {"context_tokens": context_tokens, "message_len_chars": len(message)}
    
    try:
        rules = get_routing_rules()
        logger.debug("Evaluating %d routing rules", len(rules))
    except Exception as e:
        logger.error("Failed to load routing rules: %s", str(e))
        return {"model_id": SAFE_DEFAULT, "rule": "rules_load_error"}
    
    for rule in rules:
        try:
            r_intent = rule.get("intent")
            chosen = rule.get("choose", SAFE_DEFAULT)
            chosen_norm = normalize_model_id(chosen)
            
            if chosen_norm != chosen:
                logger.debug("Normalized rule model %s -> %s", chosen, chosen_norm)
            
            # Intent-based matching
            if r_intent and first_intent and r_intent == first_intent:
                logger.debug("Intent match: %s -> %s", r_intent, chosen_norm)
                return {"model_id": chosen_norm, "rule": rule.get("name", "intent_match")}
            
            # Condition-based matching
            cond = rule.get("condition")
            if cond and _eval_condition(cond, vars):
                logger.debug("Condition match: %s -> %s", cond, chosen_norm)
                return {"model_id": chosen_norm, "rule": rule.get("name", "condition_match")}
                
        except Exception as e:
            logger.warning("Error evaluating rule %s: %s", rule.get("name", "unnamed"), str(e))
            continue
    
    # Score-based selection with error handling
    try:
        models = list_models()
        if not models:
            logger.warning("No models available in registry, using safe default")
            return {"model_id": SAFE_DEFAULT, "rule": "unavailable_registry"}
        
        logger.debug("Scoring %d available models", len(models))
        best = None
        best_score = -1e9
        
        for m in models:
            try:
                s = _score_model(m, intents or {"casual_chat"}, context_tokens)
                if s > best_score:
                    best = m
                    best_score = s
            except Exception as e:
                logger.warning("Error scoring model %s: %s", m.get("id", "unknown"), str(e))
                continue
                
        if best:
            best_id = normalize_model_id(best["id"])
            if best_id != best["id"]:
                logger.debug("Normalized scored model %s -> %s", best["id"], best_id)
            logger.debug("Selected model %s with score %.2f", best_id, best_score)
            return {"model_id": best_id, "rule": "scored_selection", "score": best_score}
    
    except Exception as e:
        logger.error("Error during model scoring: %s", str(e))
    
    logger.debug("Falling back to safe default: %s", SAFE_DEFAULT)
    return {"model_id": SAFE_DEFAULT, "rule": "final_default"}

__all__ = ["route_model"]
