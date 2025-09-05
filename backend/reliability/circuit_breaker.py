"""Circuit breaker implementation (Step 3).

Simple in-memory circuit breaker per model id.
Environment variables:
  CIRCUIT_BREAK_THRESHOLD (default 5)
  CIRCUIT_BREAK_RESET_SECONDS (default 60)
"""
from __future__ import annotations
import time
import os
import threading
import logging
from typing import Dict, Literal

logger = logging.getLogger(__name__)

State = Literal["closed", "open", "half_open"]

class Circuit:
    __slots__ = ("failures", "state", "opened_at", "last_failure")
    def __init__(self):
        self.failures = 0
        self.state: State = "closed"
        self.opened_at: float | None = None
        self.last_failure: float | None = None

_circuits: Dict[str, Circuit] = {}
_lock = threading.RLock()  # Thread-safe access to circuit states

def _get(model: str) -> Circuit:
    with _lock:
        c = _circuits.get(model)
        if not c:
            c = Circuit()
            _circuits[model] = c
            logger.debug("🔧 Created new circuit breaker for model: %s", model)
        return c

def allow_request(model: str) -> bool:
    with _lock:
        cb = _get(model)
        reset_seconds = int(os.getenv("CIRCUIT_BREAK_RESET_SECONDS", "60"))
        if cb.state == "open":
            if cb.opened_at and (time.time() - cb.opened_at) > reset_seconds:
                cb.state = "half_open"
                logger.info("🔄 Circuit breaker for %s: open -> half_open", model)
                return True
            logger.debug("🚫 Circuit breaker BLOCKS request for %s (still open)", model)
            return False
        return True

def record_success(model: str):
    with _lock:
        cb = _get(model)
        if cb.failures > 0 or cb.state != "closed":
            logger.info("✅ Circuit breaker for %s: success - resetting", model)
        cb.failures = 0
        cb.state = "closed"
        cb.opened_at = None

def record_failure(model: str):
    with _lock:
        cb = _get(model)
        threshold = int(os.getenv("CIRCUIT_BREAK_THRESHOLD", "5"))
        cb.failures += 1
        cb.last_failure = time.time()
        logger.warning("❌ Circuit breaker for %s: failure %d/%d", model, cb.failures, threshold)
        if cb.failures >= threshold:
            cb.state = "open"
            cb.opened_at = time.time()
            logger.error("💥 Circuit breaker for %s: OPENED (failures >= %d)", model, threshold)

def get_state(model: str) -> State:
    with _lock:
        return _get(model).state

def reset(model: str):
    with _lock:
        if model in _circuits:
            _circuits.pop(model)
            logger.info("🗑️ Circuit breaker for %s: manually reset", model)

def stats():
    with _lock:
        return {m: {"failures": c.failures, "state": c.state, "opened_at": c.opened_at} for m, c in _circuits.items()}

__all__ = [
    "allow_request", "record_success", "record_failure", "get_state", "reset", "stats"
]
