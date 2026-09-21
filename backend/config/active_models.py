"""Single source of truth for currently supported Groq chat models.

Keep this file small. Changing Kuro's primary/fallback model should only
require editing the constants below (and confirming the ids on Groq).

Verified against https://console.groq.com/docs/models (2026-09-21):
  - openai/gpt-oss-120b  (production, primary)
  - openai/gpt-oss-20b   (production, fast/fallback)
"""
from __future__ import annotations

import os
from typing import Dict, List

# ---------------------------------------------------------------------------
# Live Groq models (developer / free tier)
# ---------------------------------------------------------------------------
PRIMARY_CHAT_MODEL = os.getenv("KURO_PRIMARY_MODEL", "openai/gpt-oss-120b")
FALLBACK_CHAT_MODEL = os.getenv("KURO_FALLBACK_MODEL", "openai/gpt-oss-20b")

# Fast path for structured helpers (intent / memory decision). Same as fallback.
FAST_MODEL = os.getenv("KURO_FAST_MODEL", FALLBACK_CHAT_MODEL)

# Role aliases used by llm.router.LLMRouter.get_model(...)
ROLE_MODELS: Dict[str, str] = {
    "fast": FAST_MODEL,
    "mid": PRIMARY_CHAT_MODEL,
    "main": PRIMARY_CHAT_MODEL,
    "conversation": PRIMARY_CHAT_MODEL,
    "code": FALLBACK_CHAT_MODEL,
    "reasoning": PRIMARY_CHAT_MODEL,
    "summarization": PRIMARY_CHAT_MODEL,
}

# Map retired / legacy ids onto the current Groq surface so leftover callers
# do not keep sending dead model names.
LEGACY_MODEL_ALIASES: Dict[str, str] = {
    "llama-3.1-8b-instant": FALLBACK_CHAT_MODEL,
    "llama-3.3-70b-versatile": PRIMARY_CHAT_MODEL,
    "deepseek-r1-distill-llama-70b": PRIMARY_CHAT_MODEL,
    "mixtral-8x7b-32k": PRIMARY_CHAT_MODEL,
    "mixtral-8x7b-32768": PRIMARY_CHAT_MODEL,
    "gemma2-9b-it": FALLBACK_CHAT_MODEL,
    "llama3-8b-8192": FALLBACK_CHAT_MODEL,
    "llama3-70b-8192": PRIMARY_CHAT_MODEL,
    "qwen/qwen3-32b": PRIMARY_CHAT_MODEL,
    "llama-3.3-70B-versatile": PRIMARY_CHAT_MODEL,
    "llama-3.1-8B-instant": FALLBACK_CHAT_MODEL,
}


def resolve_model_id(model_id: str | None) -> str:
    """Normalize a model id to a currently supported Groq id."""
    if not model_id:
        return PRIMARY_CHAT_MODEL
    key = model_id.strip()
    if key in LEGACY_MODEL_ALIASES:
        return LEGACY_MODEL_ALIASES[key]
    lower = key.lower()
    for legacy, replacement in LEGACY_MODEL_ALIASES.items():
        if legacy.lower() == lower:
            return replacement
    return key


def get_role_model(role: str) -> str:
    return ROLE_MODELS.get(role, PRIMARY_CHAT_MODEL)


def fallback_chain(primary: str | None = None) -> List[str]:
    """Ordered unique attempt list: primary then fallback."""
    start = resolve_model_id(primary) if primary else PRIMARY_CHAT_MODEL
    chain = [start]
    fb = resolve_model_id(FALLBACK_CHAT_MODEL)
    if fb not in chain:
        chain.append(fb)
    return chain


__all__ = [
    "PRIMARY_CHAT_MODEL",
    "FALLBACK_CHAT_MODEL",
    "FAST_MODEL",
    "ROLE_MODELS",
    "LEGACY_MODEL_ALIASES",
    "resolve_model_id",
    "get_role_model",
    "fallback_chain",
]
