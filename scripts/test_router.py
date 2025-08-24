"""Automated router test: 50 queries across categories with expected models.

Run:
  python scripts/test_router.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from backend.routing.model_router_v2 import get_best_model
from backend.config.model_config import (
    CLAUDE_SONNET, CLAUDE_OPUS, GPT_4_TURBO, GPT_4O, MIXTRAL_8x7B_GROQ,
    GEMINI_15_PRO, GEMINI_15_FLASH,
)

# Build a broad suite (~50) of deterministic rule-hit prompts
cases = []

def add_many(prompt_base: str, expected: str, count: int):
    for i in range(count):
        cases.append((f"{prompt_base} #{i+1}", expected))

add_many("summarise this text please", CLAUDE_SONNET, 8)
add_many("debug this code: ```print('hi')```", GPT_4_TURBO, 8)
add_many("solve 123+456", GPT_4_TURBO, 8)
add_many("write a creative poem about stars", CLAUDE_OPUS, 8)
add_many("need a fast realtime reply", MIXTRAL_8x7B_GROQ, 8)
add_many("translate into spanish: good morning", GEMINI_15_PRO, 5)
cases += [
    ("describe this image", GPT_4O),
    ("no obvious intent", CLAUDE_SONNET),
]


async def run():
    passed = 0
    for q, expected in cases:
        res = await get_best_model(q)
        chosen = res["chosen_model"]
        ok = chosen == expected
        if ok:
            print(f"PASS -> {q[:40]}... -> {chosen}")
            passed += 1
        else:
            print(f"FAIL -> {q[:40]}... -> {chosen} (expected {expected})")
    total = len(cases)
    print(f"\nSummary: {passed}/{total} passed")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
