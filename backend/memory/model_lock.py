"""Session-level model locking.

Ensures the same model is used throughout an active session to prevent
behavioural drift. The model is assigned on the first message of a session
(via the router) and reused for subsequent messages.

Override rules:
  - User explicitly requests coding help → allow switch to code model
  - User explicitly requests reasoning → allow switch to reasoning model
  - Context exceeds current model's token limit → allow switch to larger-context model

Storage: MongoDB session_titles collection (adds a `model_id` field).
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Dict, Any

from database.db import get_session_titles_collection

logger = logging.getLogger(__name__)

# In-memory fallback when MongoDB is unavailable
_memory_cache: Dict[str, str] = {}

# Patterns that indicate explicit model-switch-worthy requests
CODE_PATTERNS = [
    re.compile(r"\b(write|generate|debug|fix|refactor)\s+(code|function|class|script|program)\b", re.I),
    re.compile(r"\b(python|javascript|typescript|java|rust|go|c\+\+|html|css)\s+(code|snippet|example)\b", re.I),
    re.compile(r"\bcode\s+(this|that|it)\b", re.I),
    re.compile(r"\bimplement\s+(a|the|this)\b", re.I),
]

REASONING_PATTERNS = [
    re.compile(r"\b(explain|prove|derive|reason|analyze|compare)\s+(step|why|how|the)\b", re.I),
    re.compile(r"\bstep[\s-]by[\s-]step\b", re.I),
    re.compile(r"\b(logic|mathematical|proof)\b", re.I),
    re.compile(r"\bthink\s+(through|about|carefully)\b", re.I),
]


def _needs_code_model(message: str) -> bool:
    return any(p.search(message) for p in CODE_PATTERNS)


def _needs_reasoning_model(message: str) -> bool:
    return any(p.search(message) for p in REASONING_PATTERNS)


def get_locked_model(session_id: str) -> Optional[str]:
    """Return the model_id locked to this session, or None if not set."""
    try:
        col = get_session_titles_collection()
        doc = col.find_one({"session_id": session_id})
        if doc:
            model_id = doc.get("model_id")
            if model_id:
                _memory_cache[session_id] = model_id
                return model_id
    except Exception as e:
        logger.error("ModelLock: failed to read for session %s: %s", session_id, e)
    # Fallback to in-memory cache
    return _memory_cache.get(session_id)


def lock_model(session_id: str, model_id: str) -> None:
    """Assign (lock) a model to a session."""
    _memory_cache[session_id] = model_id
    try:
        col = get_session_titles_collection()
        col.update_one(
            {"session_id": session_id},
            {"$set": {"model_id": model_id}},
            upsert=True,
        )
        logger.info("ModelLock: session %s locked to model %s", session_id, model_id)
    except Exception as e:
        logger.warning("ModelLock: failed to persist lock for session %s (in-memory only): %s", session_id, e)


def resolve_model(
    session_id: str,
    user_message: str,
    router_pick: str,
    context_tokens: int = 0,
    model_max_tokens: int = 32768,
) -> Dict[str, Any]:
    """Determine which model to use, respecting the session lock.

    Logic:
      1. If no model locked → use router_pick and lock it.
      2. If locked model exists:
         a. If user explicitly requests code/reasoning → override to router_pick.
         b. If context_tokens > model_max_tokens → override to router_pick.
         c. Otherwise → reuse locked model.

    Returns:
        {"model_id": str, "source": str, "locked": bool, "override_reason": str | None}
    """
    current_lock = get_locked_model(session_id)

    if current_lock is None:
        # First message in session — lock to router's pick
        lock_model(session_id, router_pick)
        return {
            "model_id": router_pick,
            "source": "router_initial",
            "locked": True,
            "override_reason": None,
        }

    # Check override conditions
    override_reason = None

    if _needs_code_model(user_message) and router_pick != current_lock:
        override_reason = "explicit_code_request"
    elif _needs_reasoning_model(user_message) and router_pick != current_lock:
        override_reason = "explicit_reasoning_request"
    elif context_tokens > model_max_tokens:
        override_reason = "context_exceeds_model_limit"

    if override_reason:
        lock_model(session_id, router_pick)
        logger.info(
            "ModelLock: overriding session %s from %s → %s (%s)",
            session_id,
            current_lock,
            router_pick,
            override_reason,
        )
        return {
            "model_id": router_pick,
            "source": "override",
            "locked": True,
            "override_reason": override_reason,
        }

    # Reuse locked model
    return {
        "model_id": current_lock,
        "source": "session_lock",
        "locked": True,
        "override_reason": None,
    }


__all__ = ["get_locked_model", "lock_model", "resolve_model"]
