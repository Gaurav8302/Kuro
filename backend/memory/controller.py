"""
Memory Controller — Rule-Based Decision Engine

Determines whether to retrieve memories and what types to fetch
based on intent data from the classifier. Zero LLM calls.

Replaces the previous LLM-driven controller that added ~500ms
latency per turn for a simple yes/no routing decision.
"""

import logging

logger = logging.getLogger(__name__)


class MemoryController:
    """Pure rule-based memory retrieval decision engine."""

    # Intent → retrieval strategy mapping
    _STRATEGY_MAP = {
        "recall": {
            "use_memory": True,
            "types": ["fact", "preference", "event"],
            "top_k": 10,
        },
        "personal": {
            "use_memory": True,
            "types": ["fact", "preference"],
            "top_k": 7,
        },
        "general": {
            "use_memory": True,
            "types": ["fact", "preference"],
            "top_k": 6,
        },
    }

    # Intents that rarely need memory retrieval (can be overridden by personal references)
    _NO_MEMORY_INTENTS = {"greeting", "creative"}

    # Personal-reference triggers (self-referential queries should use memory)
    _PERSONAL_REF_MARKERS = {
        "my", "me", "mine", "i am", "i'm", "i have", "i've", "we", "our", "us",
        "remember", "recall", "previous", "last time", "earlier", "before",
    }

    def __init__(self, llm_client=None):
        # llm_client kept for backward compatibility but is no longer used
        pass

    async def decide(self, intent_data: dict, user_input: str = "") -> dict:
        """
        Decide memory retrieval strategy based on intent data.
        Pure rule-based — no LLM calls.

        Returns:
            {"use_memory": bool, "types": list, "top_k": int}
        """
        default = {"use_memory": False, "types": [], "top_k": 0}

        intent = (intent_data.get("intent") or "general").lower()
        needs_memory = intent_data.get("needs_memory", False)

        # Fast exit: intent doesn't need memory AND no personal reference
        if intent in self._NO_MEMORY_INTENTS and not self._has_personal_reference(user_input):
            return default

        # If intent classifier says no memory but user is self-referential, still use memory
        if not needs_memory and self._has_personal_reference(user_input):
            return {
                "use_memory": True,
                "types": ["fact", "preference", "event"],
                "top_k": 8,
            }

        # Look up strategy from the map
        strategy = self._STRATEGY_MAP.get(intent)
        if strategy:
            return dict(strategy)  # return a copy

        # Fallback: use memory_types from intent_data if available
        types = intent_data.get("memory_types", [])
        if types:
            normalized = self._normalize_types(types)
            if normalized:
                return {
                    "use_memory": True,
                    "types": normalized,
                    "top_k": 5,
                }

        return default

    @classmethod
    def _has_personal_reference(cls, text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        return any(marker in lowered for marker in cls._PERSONAL_REF_MARKERS)

    @staticmethod
    def _normalize_types(raw_types: list) -> list:
        """Normalize memory type names and deduplicate."""
        _TYPE_MAP = {
            "fact": "fact", "facts": "fact",
            "preference": "preference", "preferences": "preference",
            "event": "event", "events": "event",
        }
        seen = set()
        result = []
        for t in raw_types:
            if not isinstance(t, str):
                continue
            normalized = _TYPE_MAP.get(t.strip().lower())
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result
