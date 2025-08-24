"""
Memory trigger detection utilities.

Detects vague memory/identity queries like:
 - "Do you know me?"
 - "Do you remember me?"
 - "Do you remember our past conversation?"
 - "Who am I?"
 - "What did we talk about before?"

Implements:
 - Phrase/regex detection (fast path)
 - Optional semantic similarity using the embedding model (if available)

Return contract:
    is_memory_trigger(message, manager=None) -> (triggered: bool, confidence: float, reason: str)
"""
from __future__ import annotations

from typing import Tuple, List
import os
import re


TRIGGER_PHRASES: List[str] = [
    "do you know me",
    "do you remember me",
    "do you remember our past conversation",
    "do you remember our last conversation",
    "do you remember our conversation",
    "who am i",
    "what did we talk about before",
    "what did we discuss before",
    "do you remember me from before",
    "do you remember who i am",
    "remember me",
    "do you know who i am",
    # Additional common variants
    "do you remember our chat",
    "do you recall me",
    "do you recall who i am",
    "remember who i am",
    "do you recall our conversation",
    "do you remember my name",
    "what's my name",
    "whats my name",
    "who was i",
]

TRIGGER_REGEX: List[re.Pattern] = [
    re.compile(r"\b(remember|know)\b\s+(me|who i am)", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
    re.compile(r"\b(what|which)\s+did\s+we\s+(talk|discuss)\s+before\b", re.IGNORECASE),
    re.compile(r"\bremember\s+our\s+(past|last)\s+conversation\b", re.IGNORECASE),
    re.compile(r"\b(what'?s|what is)\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+(remember|recall)\s+(me|who i am)\b", re.IGNORECASE),
]

SEMANTIC_CANONICALS: List[str] = [
    "do you remember me",
    "do you know who i am",
    "who am i",
    "do you remember our past conversation",
    "what did we talk about before",
]


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    try:
        import math
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(a * a for a in v2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)
    except Exception:
        return 0.0


def is_memory_trigger(message: str, manager=None, semantic_threshold: float = 0.82) -> Tuple[bool, float, str]:
    """Return whether message is a memory/identity recall query.

    Args:
        message: user message text
        manager: optional memory manager providing get_embedding(text) -> List[float]
        semantic_threshold: threshold for semantic match

    Returns:
        (triggered, confidence, reason)
    """
    if not message:
        return False, 0.0, "empty"

    m = message.strip().lower()

    # Allow override via env var to tune sensitivity without code changes
    try:
        env_thresh = os.getenv("MEM_TRIGGER_SEMANTIC_THRESHOLD")
        if env_thresh:
            semantic_threshold = float(env_thresh)
    except Exception:
        pass

    # Phrase fast-path
    for p in TRIGGER_PHRASES:
        if p in m:
            return True, 0.95, f"phrase:{p}"

    # Regex fast-path
    for rx in TRIGGER_REGEX:
        if rx.search(message):
            return True, 0.9, "regex"

    # Semantic similarity (best-effort)
    try:
        if manager and hasattr(manager, "get_embedding"):
            q_emb = manager.get_embedding(message)
            if isinstance(q_emb, list) and q_emb:
                best = 0.0
                for can in SEMANTIC_CANONICALS:
                    c_emb = manager.get_embedding(can)
                    if not isinstance(c_emb, list) or not c_emb:
                        continue
                    sim = _cosine_similarity(q_emb, c_emb)
                    if sim > best:
                        best = sim
                if best >= semantic_threshold:
                    return True, float(best), "semantic"
    except Exception:
        # Silent degrade; just means we didn't trigger semantically
        pass

    return False, 0.0, "none"


__all__ = ["is_memory_trigger", "TRIGGER_PHRASES", "SEMANTIC_CANONICALS"]
