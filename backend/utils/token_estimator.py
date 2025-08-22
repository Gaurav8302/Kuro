"""Token estimation utilities (Step 5).

Provides lightweight approximate token counting & trimming.
Assumptions: ~4 chars per token average (English) if no model-specific logic.
"""
from __future__ import annotations
from typing import List, Dict, Any

AVG_CHARS_PER_TOKEN = 4

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # quick heuristic
    return max(1, len(text) // AVG_CHARS_PER_TOKEN)

def estimate_messages(messages: List[Dict[str, str]]) -> int:
    total = 0
    for m in messages:
        total += estimate_tokens(m.get("content", ""))
    return total

def trim_messages(messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
    """Trim from oldest user/assistant messages preserving system if present."""
    if estimate_messages(messages) <= max_tokens:
        return messages
    # Preserve last messages; drop from start (after any initial system)
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
    kept = []
    # Keep newest non-system messages until limit reached (reverse accumulate)
    rev = list(reversed(non_system))
    acc_rev = []
    running = estimate_messages(system_msgs)
    for m in rev:
        mtoks = estimate_tokens(m.get("content", ""))
        if running + mtoks > max_tokens:
            break
        acc_rev.append(m)
        running += mtoks
    trimmed = system_msgs + list(reversed(acc_rev))
    return trimmed

__all__ = ["estimate_tokens", "estimate_messages", "trim_messages"]
