"""Simple routing smoke tests for model selection and fallback chains.

Runs deterministic queries that match rule-based patterns so the chosen model
is predictable. Uses the v2 router: get_best_model and build_fallback_chain.

Usage:
  python scripts/test_model_routing.py
"""
from __future__ import annotations
import asyncio
import sys
from typing import List, Tuple

# Ensure project root is on path when running directly
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from backend.routing.model_router_v2 import get_best_model, build_fallback_chain
from backend.config.model_config import (
    CLAUDE_SONNET,
    CLAUDE_OPUS,
    GPT_4_TURBO,
    GPT_4O,
    MIXTRAL_8x7B_GROQ,
    GEMINI_15_PRO,
    GEMINI_15_FLASH,
)


# Each tuple: (query, expected_model, category)
TEST_CASES: List[Tuple[str, str, str]] = [
    ("please summarise this quickly", CLAUDE_SONNET, "summary"),
    ("debug this code: ```print('hi')```", GPT_4_TURBO, "coding"),
    ("solve 2+2 and explain", GPT_4_TURBO, "math"),
    ("write a creative short story about a robot", CLAUDE_OPUS, "creative"),
    ("need a fast realtime answer", MIXTRAL_8x7B_GROQ, "fast"),
    ("translate this into spanish: hello world", GEMINI_15_PRO, "translate"),
    ("describe this image in detail", GPT_4O, "vision"),
    # No rule match -> default router selection (LLM router default to Claude Sonnet)
    ("asdkjhasdhqwe", CLAUDE_SONNET, "default"),
]


async def run_case(query: str, expected: str, category: str) -> bool:
    res = await get_best_model(query)
    chosen = res["chosen_model"]
    ok = chosen == expected
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {category:9s} -> chosen={chosen} expected={expected} reason={res['reason']} conf={res['confidence']}")
    return ok


async def main() -> None:
    print("Routing decisions:\n-------------------")
    passed = 0
    for q, expected, cat in TEST_CASES:
        ok = await run_case(q, expected, cat)
        passed += int(ok)
    total = len(TEST_CASES)
    print("\nFallback chains:\n----------------")
    chain = build_fallback_chain(GEMINI_15_PRO)
    print(f"GEMINI_15_PRO chain: {chain}")
    assert chain == [GEMINI_15_PRO, GEMINI_15_FLASH, GPT_4O]

    print("\nSummary:\n--------")
    print(f"PASSED {passed}/{total}")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
