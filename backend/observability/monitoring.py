"""Monitoring utilities: track routing decisions, fallbacks, agreement rates.

Backed by in-memory counters for simplicity; can be extended to metrics DB.
"""
from __future__ import annotations
import time
from typing import Dict, Any

_counters: Dict[str, float] = {
    "routing.calls": 0,
    "routing.fallbacks": 0,
    "routing.cache_hits": 0,
    "routing.rule_hits": 0,
    "routing.router_hits": 0,
}

_timings: Dict[str, float] = {"routing.total_latency_ms": 0.0}
_last_week_rollup_at = time.time()


def inc(key: str, value: float = 1.0):
    _counters[key] = _counters.get(key, 0.0) + value


def add_time(key: str, ms: float):
    _timings[key] = _timings.get(key, 0.0) + ms


def observe_routing(call_latency_ms: float, used_fallback: bool, via: str, cache_hit: bool = False):
    inc("routing.calls")
    add_time("routing.total_latency_ms", call_latency_ms)
    if used_fallback:
        inc("routing.fallbacks")
    if cache_hit:
        inc("routing.cache_hits")
    if via == "rule":
        inc("routing.rule_hits")
    elif via == "router":
        inc("routing.router_hits")


def snapshot() -> Dict[str, Any]:
    calls = _counters.get("routing.calls", 0.0) or 1.0
    return {
        **_counters,
        **_timings,
        "routing.avg_latency_ms": _timings.get("routing.total_latency_ms", 0.0) / calls,
        "ts": time.time(),
    }


__all__ = ["observe_routing", "snapshot"]
