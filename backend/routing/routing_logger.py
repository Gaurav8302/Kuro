"""Structured JSONL logger for routing decisions.

Every routing decision is appended to ``logs/routing_decisions.jsonl``
so that engineers can review model selection, latency, and research
triggers after the fact.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "routing_decisions.jsonl")


def log_routing_decision(
    query: str,
    chosen_model: str,
    task_type: str,
    complexity: str,
    research_required: bool,
    confidence: float,
    latency_ms: int,
    fallback_used: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a routing decision record to the JSONL log file."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query[:500],
        "chosen_model": chosen_model,
        "task_type": task_type,
        "complexity": complexity,
        "research_required": research_required,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "fallback_used": fallback_used,
    }
    if extra:
        record.update(extra)

    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write routing log: %s", e)
