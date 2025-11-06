"""Advanced model router with hybrid intent detection and fallbacks.

Simplified to use skill-based routing with 4 flagship models:
- conversation: llama-3.3-70b-versatile (Groq - fast chat)
- reasoning: deepseek-r1-distill-llama-70b (Groq - complex reasoning)
- code: llama-3.1-8b-instant (Groq - code generation)
- summarization: mixtral-8x7b-32k (Groq - long context)

Routing priority:
1. Forced override (developer/user specified model)
2. Skill-based mapping (deterministic intent → model)
3. Score-based routing (optional, env-controlled)

Exports:
- rule_based_router(query) -> (model, confidence, reason)
- get_best_model(query, session_id=None, history=None, system=None) -> dict
- execute_with_fallbacks(model_chain, query, system=None) -> (reply, used_model, fallback_used)
- build_fallback_chain(model) -> list

Meets requirements: speed, reliability, accuracy, maintainability, observability.
"""
from __future__ import annotations
import asyncio
import re
import time
import logging
import threading
import os
from typing import Dict, Any, List, Optional, Tuple

from config.model_config import (
    get_fallback_chain,
    get_model_source,
    normalize_model_id,
    KIMMI_CONVERSATIONAL,
    DEEPSEEK_REASONING,
    GROQ_CODE,
    SUMMARIZER_MEMORY,
    SKILL_TO_MODEL,
)
from observability.instrumentation_middleware import update_llm_call

logger = logging.getLogger(__name__)

# Environment-controlled routing strategy
ROUTING_STRATEGY = os.getenv("ROUTING_STRATEGY", "skill").lower()  # "skill" or "score"
ENABLE_SCORE_ROUTING = os.getenv("ENABLE_SCORE_ROUTING", "false").lower() == "true"

# Thread-safe in-memory caches with locks
_cache_lock = threading.RLock()
_route_cache: Dict[str, Tuple[str, float]] = {}
_last_model_per_session: Dict[str, str] = {}
_CACHE_TTL = 300.0  # seconds

# ========================================
# SKILL-BASED ROUTING CONFIGURATION
# ========================================

# Intent-to-skill mapping (maps detected intents to skills)
INTENT_TO_SKILL: Dict[str, str] = {
    # Conversation intents
    "casual_chat": "conversation",
    "greeting": "conversation",
    "chitchat": "conversation",
    "general": "conversation",
    
    # Reasoning intents
    "complex_reasoning": "reasoning",
    "math_solver": "reasoning",
    "analysis": "reasoning",
    "fact_check": "reasoning",
    "logic": "reasoning",
    
    # Code intents
    "code_generation": "code",
    "debugging": "code",
    "explain_code": "code",
    "code": "code",
    
    # Summarization intents
    "long_context_summary": "summarization",
    "summarization": "summarization",
    "memory": "summarization",
    "compression": "summarization",
}

# Keyword patterns for quick skill detection (regex-based)
SKILL_KEYWORD_PATTERNS: Dict[str, List[str]] = {
    "code": [
        r"```",  # Code block
        r"\bcode\b",
        r"\bdebug(ging)?\b",
        r"\bfunction\b",
        r"\bclass\b",
        r"\bimport\b",
        r"\berror\b",
        r"\bstacktrace\b",
    ],
    "reasoning": [
        r"\bsolve\b",
        r"\bprove\b",
        r"\banalyze\b",
        r"\breason(ing)?\b",
        r"\bstep by step\b",
        r"\blogic\b",
        r"\bderive\b",
        r"\bmath(ematics)?\b",
    ],
    "summarization": [
        r"\bsummariz(e|ing|ation)\b",
        r"\btl;?dr\b",  # Matches "tldr" and "tl;dr"
        r"\bcondense\b",
        r"\babstract\b",
        r"\bshorten\b",
        r"\bcompress\b",
    ],
}


def _now() -> float:
    return time.time()


def detect_skill_from_query(query: str) -> Optional[str]:
    """Detect skill from query using keyword patterns."""
    text = query.lower()
    
    # Check each skill's patterns
    for skill, patterns in SKILL_KEYWORD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                logger.debug(f"Detected skill '{skill}' from pattern: {pattern}")
                return skill
    
    return None


def rule_based_router(query: str, intent: Optional[str] = None) -> Tuple[Optional[str], float, str]:
    """Simplified rule-based router using skill mapping.
    
    Priority:
    1. Intent-to-skill mapping (if intent provided)
    2. Keyword pattern detection
    3. Default to conversation
    """
    # Try intent-to-skill mapping first
    if intent and intent in INTENT_TO_SKILL:
        skill = INTENT_TO_SKILL[intent]
        model = SKILL_TO_MODEL[skill]
        model = normalize_model_id(model)
        logger.debug(f"Intent '{intent}' → skill '{skill}' → model '{model}'")
        return model, 0.95, f"skill_map:intent={intent}:skill={skill}"
    
    # Try keyword pattern detection
    skill = detect_skill_from_query(query)
    if skill:
        model = SKILL_TO_MODEL[skill]
        model = normalize_model_id(model)
        logger.debug(f"Query pattern → skill '{skill}' → model '{model}'")
        return model, 0.90, f"skill_map:pattern:skill={skill}"
    
    # Default to conversation skill
    model = normalize_model_id(SKILL_TO_MODEL["conversation"])
    logger.debug(f"No skill detected, defaulting to conversation: {model}")
    return model, 0.75, "skill_map:default:conversation"


async def llm_router(query: str, history: Optional[List[Dict[str, str]]] = None, system: Optional[str] = None) -> Tuple[str, float, str]:
    """Legacy LLM router - now defaults to conversation model.
    
    Note: This is kept for backward compatibility but now uses skill-based routing.
    """
    del history, system  # unused
    await asyncio.sleep(0)  # yield control
    
    # Default to conversation model
    model = normalize_model_id(KIMMI_CONVERSATIONAL)
    return model, 0.7, "llm_router_default:conversation"


async def get_best_model(
    query: str, 
    session_id: Optional[str] = None, 
    history: Optional[List[Dict[str, str]]] = None, 
    system: Optional[str] = None,
    intent: Optional[str] = None,
    forced_model: Optional[str] = None
) -> Dict[str, Any]:
    """Get best model using simplified skill-based routing.
    
    Priority:
    1. Forced override (developer/user specified model)
    2. Cache hit (recent similar query)
    3. Rule-based (skill mapping from intent or keywords)
    4. Score-based (optional, env-controlled)
    5. Default (conversation model)
    
    Returns:
        dict with keys: chosen_model, source, reason, confidence, fallback_used
    """
    # PRIORITY 1: Forced override
    if forced_model:
        forced_model = normalize_model_id(forced_model)
        logger.info(f"🎯 Forced model override: {forced_model}")
        return {
            "chosen_model": forced_model,
            "source": get_model_source(forced_model),
            "reason": "forced_override",
            "confidence": 1.0,
            "fallback_used": False,
        }
    
    # PRIORITY 2: Cache check
    key = query.strip().lower()[:128]
    now = _now()
    
    with _cache_lock:
        if key in _route_cache:
            model, ts = _route_cache[key]
            if now - ts < _CACHE_TTL:
                model = normalize_model_id(model)
                logger.debug("🔄 Cache hit for query fragment: %s -> %s", key[:50], model)
                return {
                    "chosen_model": model,
                    "source": get_model_source(model),
                    "reason": "cache_hit",
                    "confidence": 0.95,
                    "fallback_used": False,
                }
            else:
                _route_cache.pop(key, None)
                logger.debug("🗑️ Expired cache entry removed for query: %s", key[:50])

    # PRIORITY 3: Rule-based skill routing
    rb_model, rb_conf, rb_reason = rule_based_router(query, intent=intent)
    if rb_model and rb_conf >= 0.75:
        rb_model_norm = normalize_model_id(rb_model)
        
        with _cache_lock:
            _route_cache[key] = (rb_model_norm, now)
        
        logger.debug("✅ Skill-based selection: %s (confidence: %.2f)", rb_model_norm, rb_conf)
        
        result = {
            "chosen_model": rb_model_norm,
            "source": get_model_source(rb_model_norm),
            "reason": rb_reason,
            "confidence": rb_conf,
            "fallback_used": False,
        }
        
        try:
            await update_llm_call({
                "routing_reason": result["reason"],
                "model_selected": result["chosen_model"],
                "router_confidence": result["confidence"],
            })
        except Exception:
            pass
        
        return result

    # PRIORITY 4: Score-based routing (optional, env-controlled)
    if ENABLE_SCORE_ROUTING and ROUTING_STRATEGY == "score":
        logger.warning("⚠️ Score-based routing not fully implemented yet, falling back to conversation")
        # TODO: Implement score-based routing if needed
        # For now, fall through to default
    
    # PRIORITY 5: Default to conversation model
    model = normalize_model_id(KIMMI_CONVERSATIONAL)
    reason = "default:conversation"
    conf = 0.6
    logger.debug("🔻 No high-confidence match, defaulting to conversation model: %s", model)

    # Sticky last model per session for stability (thread-safe)
    if session_id:
        with _cache_lock:
            last = _last_model_per_session.get(session_id)
            if last and last == model:
                reason += ":sticky_session"
                conf = max(conf, 0.7)
                logger.debug("📌 Sticky session model: %s", model)
            _last_model_per_session[session_id] = model

    # Update cache thread-safely
    with _cache_lock:
        _route_cache[key] = (model, now)

    result = {
        "chosen_model": model,
        "source": get_model_source(model),
        "reason": reason,
        "confidence": float(conf),
        "fallback_used": False,
    }
    
    try:
        await update_llm_call({
            "routing_reason": result["reason"],
            "model_selected": result["chosen_model"],
            "router_confidence": result["confidence"],
        })
    except Exception:
        pass
    
    return result


async def execute_with_fallbacks(model_chain: List[str], query: str, system: Optional[str] = None) -> Tuple[str, str, bool]:
    """Execute query with simplified fallback chain (max 2 backups).
    
    Returns:
        (response, used_model, fallback_used)
    """
    # Limit chain to max 3 models (primary + 2 backups)
    model_chain = model_chain[:3]
    
    logger.debug("🔄 Starting fallback execution chain: %s", model_chain)
    
    last_err: Optional[Exception] = None
    for idx, model in enumerate(model_chain):
        try:
            # Normalize model ID for consistency
            model = normalize_model_id(model)
            logger.debug("🎯 Trying model %d/%d: %s", idx + 1, len(model_chain), model)
            
            if model.startswith("fail:"):
                raise RuntimeError("simulated failure")
            
            # Minimal placeholder response
            reply = f"[model:{model}] OK"
            
            # Log fallback usage if not the first model
            if idx > 0:
                logger.warning("⚠️ Fallback used: model %d succeeded (%s)", idx + 1, model)
                try:
                    await update_llm_call({
                        "fallback_hop": idx,
                        "model_selected": model,
                    })
                except Exception as telemetry_err:
                    logger.error("❌ Telemetry error: %s", telemetry_err)
            else:
                logger.debug("✅ Primary model succeeded: %s", model)
            
            return reply, model, idx > 0
            
        except Exception as e:
            last_err = e
            logger.warning("❌ Model %s failed: %s", model, e)
            continue
    
    # All models failed
    error_msg = f"All {len(model_chain)} models failed; last_error={last_err}"
    logger.error("💥 %s", error_msg)
    raise RuntimeError(error_msg)


def build_fallback_chain(primary_model: str) -> List[str]:
    """Build simplified fallback chain (max 2 backups)."""
    chain = get_fallback_chain(primary_model)
    # Ensure max 3 models total (primary + 2 backups)
    return chain[:3]


__all__ = [
    "rule_based_router",
    "llm_router",
    "get_best_model",
    "execute_with_fallbacks",
    "build_fallback_chain",
    "detect_skill_from_query",
    "SKILL_TO_MODEL",
    "INTENT_TO_SKILL",
]
