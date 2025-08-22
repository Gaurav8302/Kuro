import asyncio
import time
import pytest

from routing.model_router_v2 import rule_based_router, get_best_model, execute_with_fallbacks, build_fallback_chain
from config.model_config import (
    CLAUDE_SONNET, CLAUDE_OPUS, CLAUDE_HAIKU,
    GPT_4_TURBO, GPT_4O, GPT_35_TURBO,
    MIXTRAL_8x7B_OR, MIXTRAL_8x7B_GROQ, LLAMA3_8B_GROQ,
    GEMINI_15_PRO, GEMINI_15_FLASH,
)


def test_rule_based_fast_code_and_summary():
    m, c, r = rule_based_router("please summarise this quickly")
    assert m == CLAUDE_SONNET and c >= 0.8
    m2, c2, r2 = rule_based_router("debug this code: ```print('hi')```")
    assert m2 == GPT_4_TURBO and c2 >= 0.8


@pytest.mark.asyncio
async def test_best_model_cache_and_default():
    t0 = time.time()
    res1 = await get_best_model("tell me a story about a dragon")
    assert res1["chosen_model"] in {CLAUDE_OPUS, CLAUDE_SONNET}
    res2 = await get_best_model("tell me a story about a dragon")
    assert res2["reason"] == "cache_hit"
    assert res2["confidence"] >= 0.9
    assert res2["chosen_model"] == res1["chosen_model"]


@pytest.mark.asyncio
async def test_execute_with_fallbacks_simulated():
    chain = ["fail:" + CLAUDE_SONNET, CLAUDE_OPUS, CLAUDE_HAIKU]
    reply, used, fb = await execute_with_fallbacks(chain, "hello")
    assert used == CLAUDE_OPUS and fb is True
    assert reply.startswith("[model:")


def test_fallback_chain_shapes():
    chain = build_fallback_chain(GEMINI_15_PRO)
    assert chain == [GEMINI_15_PRO, GEMINI_15_FLASH, GPT_4O]
    chain2 = build_fallback_chain(MIXTRAL_8x7B_OR)
    assert chain2 == [MIXTRAL_8x7B_OR, MIXTRAL_8x7B_GROQ, LLAMA3_8B_GROQ]
