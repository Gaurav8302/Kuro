"""Fallback routing logic (Step 3/4 combined initial).

Decides next model on failure using registry's fallback list.
"""
from __future__ import annotations
from typing import Optional
from config.config_loader import get_model


def choose_fallback(current_model: str) -> Optional[str]:
    m = get_model(current_model)
    if not m:
        return None
    for fb in m.get("fallback", []):
        fm = get_model(fb)
        if fm:  # Could add health checks later
            return fb
    return None

__all__ = ["choose_fallback"]
