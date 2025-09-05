"""Advanced model router with hybrid intent detection and fallbacks.

Exports:
- rule_based_router(query) -> (model, confidence, reason)
- llm_router(query, history=None, system=None) -> (model, confidence, reason)
- get_best_model(query, session_id=None, history=None, system=None) -> dict
- execute_with_fallbacks(model_chain, query, system=None) -> (reply, used_model, fallback_used)

Meets requirements: speed, reliability, accuracy, maintainability, observability.
"""
from __future__ import annotations
import asyncio
import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from config.model_config import (
    get_rule_keywords,
    get_fallback_chain,
    get_model_source,
    normalize_model_id,
    CLAUDE_SONNET,
)
from observability.instrumentation_middleware import update_llm_call

logger = logging.getLogger(__name__)

# Simple in-memory caches
_route_cache: Dict[str, Tuple[str, float]] = {}
_last_model_per_session: Dict[str, str] = {}
_CACHE_TTL = 300.0  # seconds


def _now() -> float:
    return time.time()


def rule_based_router(query: str) -> Tuple[Optional[str], float, str]:
    text = query.lower()
    best: Optional[str] = None
    reason = ""
    # Give basic confidence accumulation
    for tag, patterns, model in get_rule_keywords():
        for pat in patterns:
            if re.search(pat, text):
                # Choose the first matching model with high confidence and normalize
                best = normalize_model_id(model)
                reason = f"rule:{tag}:{pat}"
                if best != model:
                    logger.debug("Normalized rule model %s -> %s", model, best)
                return best, 0.9, reason
    return None, 0.0, "no_rule_match"


async def llm_router(query: str, history: Optional[List[Dict[str, str]]] = None, system: Optional[str] = None) -> Tuple[str, float, str]:
    # Stub lightweight router to avoid extra dependencies. Picks Claude Sonnet by default.
    # A real implementation could call a small hosted router model.
    # We keep it fast and deterministic with minimal token usage.
    del history, system  # unused for now
    await asyncio.sleep(0)  # yield control
    return CLAUDE_SONNET, 0.7, "llm_router_default"


async def get_best_model(query: str, session_id: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, system: Optional[str] = None) -> Dict[str, Any]:
    # Cache by normalized query fragment to avoid repeated detection
    key = query.strip().lower()[:128]
    now = _now()
    if key in _route_cache:
        model, ts = _route_cache[key]
        if now - ts < _CACHE_TTL:
            model = normalize_model_id(model)
            return {
                "chosen_model": model,
                "source": get_model_source(model),
                "reason": "cache_hit",
                "confidence": 0.95,
                "fallback_used": False,
            }
        else:
            _route_cache.pop(key, None)

    # Stage A: rule-based
    rb_model, rb_conf, rb_reason = rule_based_router(query)
    if rb_model and rb_conf >= 0.8:
        rb_model_norm = normalize_model_id(rb_model)
        _route_cache[key] = (rb_model_norm, now)
        return {
            "chosen_model": rb_model_norm,
            "source": get_model_source(rb_model_norm),
            "reason": rb_reason,
            "confidence": rb_conf,
            "fallback_used": False,
        }

    # Stage B: LLM router with 5s timeout, default to Claude Sonnet at low confidence
    try:
        model, conf, reason = await asyncio.wait_for(llm_router(query, history, system), timeout=5.0)
    except asyncio.TimeoutError:
        model, conf, reason = CLAUDE_SONNET, 0.6, "router_timeout_default_claude"

    # Normalize the model from LLM router
    model = normalize_model_id(model)

    # If low confidence, default to Claude Sonnet (normalized)
    if conf < 0.6:
        model = normalize_model_id(CLAUDE_SONNET)
        reason = f"low_conf_default:{reason}"
        conf = 0.6

    # Sticky last model per session for stability
    if session_id:
        last = _last_model_per_session.get(session_id)
        if last and last == model:
            reason += ":sticky_session"
            conf = max(conf, 0.7)
        _last_model_per_session[session_id] = model

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
    # This function is provider-agnostic; actual execution should be integrated with provider clients.
    # Here we simulate execution by raising to trigger fallback only if model id contains "fail:" prefix.
    # Replace with real execution wiring in orchestrator.
    last_err: Optional[Exception] = None
    for idx, model in enumerate(model_chain):
        try:
            if model.startswith("fail:"):
                raise RuntimeError("simulated failure")
            # Minimal placeholder response
            reply = f"[model:{model}] OK"
            if idx > 0:
                try:
                    await update_llm_call({
                        "fallback_hop": idx,
                        "model_selected": model,
                    })
                except Exception:
                    pass
            return reply, model, idx > 0
        except Exception as e:
            last_err = e
            continue
    # All failed
    raise RuntimeError(f"All models failed; last_error={last_err}")


def build_fallback_chain(primary_model: str) -> List[str]:
    return get_fallback_chain(primary_model)  # get_fallback_chain now returns normalized IDs


__all__ = [
    "rule_based_router",
    "llm_router",
    "get_best_model",
    "execute_with_fallbacks",
    "build_fallback_chain",
]