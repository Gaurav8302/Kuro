"""Circuit breaker implementation (Step 3).

Simple in-memory circuit breaker per model id.
Environment variables:
  CIRCUIT_BREAK_THRESHOLD (default 5)
  CIRCUIT_BREAK_RESET_SECONDS (default 60)
"""
from __future__ import annotations
import time
import os
from typing import Dict, Literal

State = Literal["closed", "open", "half_open"]

class Circuit:
    __slots__ = ("failures", "state", "opened_at", "last_failure")
    def __init__(self):
        self.failures = 0
        self.state: State = "closed"
        self.opened_at: float | None = None
        self.last_failure: float | None = None

_circuits: Dict[str, Circuit] = {}

def _get(model: str) -> Circuit:
    c = _circuits.get(model)
    if not c:
        c = Circuit()
        _circuits[model] = c
    return c

def allow_request(model: str) -> bool:
    cb = _get(model)
    reset_seconds = int(os.getenv("CIRCUIT_BREAK_RESET_SECONDS", "60"))
    if cb.state == "open":
        if cb.opened_at and (time.time() - cb.opened_at) > reset_seconds:
            cb.state = "half_open"
            return True
        return False
    return True

def record_success(model: str):
    cb = _get(model)
    cb.failures = 0
    cb.state = "closed"
    cb.opened_at = None

def record_failure(model: str):
    cb = _get(model)
    threshold = int(os.getenv("CIRCUIT_BREAK_THRESHOLD", "5"))
    cb.failures += 1
    cb.last_failure = time.time()
    if cb.failures >= threshold:
        cb.state = "open"
        cb.opened_at = time.time()

def get_state(model: str) -> State:
    return _get(model).state

def reset(model: str):
    if model in _circuits:
        _circuits.pop(model)

def stats():
    return {m: {"failures": c.failures, "state": c.state, "opened_at": c.opened_at} for m, c in _circuits.items()}

__all__ = [
    "allow_request", "record_success", "record_failure", "get_state", "reset", "stats"
]
