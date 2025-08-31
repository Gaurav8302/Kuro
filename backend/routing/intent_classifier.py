"""Intent classification (rule-based first pass).

Returns set of intents from spec:
  - casual_chat
  - long_context_summary
  - complex_reasoning
  - tool_use_or_function_call
  - high_creativity_generation
"""
from __future__ import annotations
import re
from typing import Set, Optional

KEYWORDS = {
    "tool_use_or_function_call": [r"call (the )?api", r"invoke function", r"tool:\w+", r"function call"],
    "long_context_summary": [r"summari[sz]e", r"long document", r"condense", r"tl;dr"],
    "complex_reasoning": [r"prove", r"derive", r"analyze deeply", r"step by step", r"logic puzzle"],
    "high_creativity_generation": [r"story", r"poem", r"creative", r"imagine", r"novel idea"],
}

FORCE_INTENT_PREFIX = "INTENT:"

def classify_intent(message: str, developer_override: Optional[str] = None) -> Set[str]:
    intents: Set[str] = set()
    text = message.lower()
    # developer override
    if developer_override:
        intents.add(developer_override)
        return intents
    # inline force pattern "INTENT:complex_reasoning" for quick testing
    if FORCE_INTENT_PREFIX.lower() in text:
        after = text.split(FORCE_INTENT_PREFIX.lower(),1)[1].strip().split()[0]
        intents.add(after)
        return intents
    matched_any = False
    for intent, patterns in KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, text):
                intents.add(intent)
                matched_any = True
    if not matched_any:
        intents.add("casual_chat")
    return intents

__all__ = ["classify_intent"]
