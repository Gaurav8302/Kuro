"""Fallback routing: primary → fallback from the active model registry."""
from __future__ import annotations

from typing import Optional

from config.active_models import FALLBACK_CHAT_MODEL, resolve_model_id
from config.config_loader import get_model


def choose_fallback(current_model: str) -> Optional[str]:
    current = resolve_model_id(current_model)
    m = get_model(current)
    if m:
        for fb in m.get("fallback", []):
            resolved = resolve_model_id(fb)
            if resolved and resolved != current:
                return resolved
    # Hard guarantee: always try the configured fallback once
    fb = resolve_model_id(FALLBACK_CHAT_MODEL)
    if fb != current:
        return fb
    return None


__all__ = ["choose_fallback"]
