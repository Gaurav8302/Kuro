"""Thread-safe in-memory router cache with TTL.

Provides a simple cache for routing decisions to avoid redundant
LLM classifier calls for repeated or similar queries.

Cache key: first 128 characters of lowercased, stripped query.
Cache TTL: 300 seconds (5 minutes).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

_lock = threading.RLock()
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 300.0  # seconds


def _make_key(query: str) -> str:
    return query.strip().lower()[:128]


def get(query: str) -> Optional[Dict[str, Any]]:
    """Return cached routing decision or None if miss/expired."""
    key = _make_key(query)
    now = time.time()
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        if now - entry["_ts"] > _CACHE_TTL:
            _cache.pop(key, None)
            return None
        return entry


def put(query: str, decision: Dict[str, Any]) -> None:
    """Store a routing decision in the cache."""
    key = _make_key(query)
    with _lock:
        _cache[key] = {**decision, "_ts": time.time()}


def invalidate(query: str) -> None:
    """Remove a specific cache entry."""
    key = _make_key(query)
    with _lock:
        _cache.pop(key, None)


def clear() -> None:
    """Clear all cached routing decisions."""
    with _lock:
        _cache.clear()
