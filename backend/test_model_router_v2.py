import asyncio
import time
import pytest

from routing.model_router_v2 import (
    rule_based_router, 
    get_best_model, 
    execute_with_fallbacks, 
    build_fallback_chain,
    detect_skill_from_query,
)
from config.model_config import (
    KIMMI_CONVERSATIONAL,
    DEEPSEEK_REASONING,
    GROQ_CODE,
    SUMMARIZER_MEMORY,
    normalize_model_id,
)


def test_skill_detection_from_keywords():
    """Test skill detection from keyword patterns."""
    # Code skill
    assert detect_skill_from_query("debug this code: ```print('hi')```") == "code"
    assert detect_skill_from_query("write a function to sort") == "code"
    
    # Reasoning skill
    assert detect_skill_from_query("solve this math problem step by step") == "reasoning"
    assert detect_skill_from_query("analyze the logic behind this") == "reasoning"
    
    # Summarization skill
    assert detect_skill_from_query("please summarize this article") == "summarization"
    assert detect_skill_from_query("tl;dr of this document") == "summarization"
    
    # No skill detected
    assert detect_skill_from_query("hello there") is None


def test_rule_based_conversation():
    """Test rule-based routing for conversation."""
    m, c, r = rule_based_router("hello, how are you?")
    assert m == normalize_model_id(KIMMI_CONVERSATIONAL)
    assert c >= 0.75
    assert "conversation" in r.lower()


def test_rule_based_reasoning():
    """Test rule-based routing for reasoning tasks."""
    m, c, r = rule_based_router("solve: 2x + 5 = 15", intent="math_solver")
    assert m == normalize_model_id(DEEPSEEK_REASONING)
    assert c >= 0.90
    assert "reasoning" in r.lower()


def test_rule_based_code():
    """Test rule-based routing for code generation."""
    m, c, r = rule_based_router("write a Python function to reverse a string")
    assert m == normalize_model_id(GROQ_CODE)
    assert c >= 0.85
    assert "code" in r.lower()


def test_rule_based_summarization():
    """Test rule-based routing for summarization."""
    m, c, r = rule_based_router("please summarize this long article for me")
    assert m == normalize_model_id(SUMMARIZER_MEMORY)
    assert c >= 0.85
    assert "summarization" in r.lower()


@pytest.mark.asyncio
async def test_get_best_model_forced_override():
    """Test forced model override takes priority."""
    forced = "deepseek-r1-distill-llama-70b"
    res = await get_best_model("hello", forced_model=forced)
    assert res["chosen_model"] == normalize_model_id(forced)
    assert res["reason"] == "forced_override"
    assert res["confidence"] == 1.0


@pytest.mark.asyncio
async def test_get_best_model_cache():
    """Test caching mechanism."""
    query = "tell me a story about a dragon"
    
    # First call
    res1 = await get_best_model(query)
    assert res1["chosen_model"] in [
        normalize_model_id(KIMMI_CONVERSATIONAL),
        normalize_model_id(DEEPSEEK_REASONING),
        normalize_model_id(GROQ_CODE),
        normalize_model_id(SUMMARIZER_MEMORY),
    ]
    
    # Second call should hit cache
    res2 = await get_best_model(query)
    assert res2["reason"] == "cache_hit"
    assert res2["confidence"] >= 0.9
    assert res2["chosen_model"] == res1["chosen_model"]


@pytest.mark.asyncio
async def test_get_best_model_intent_routing():
    """Test intent-based routing."""
    # Casual chat intent
    res1 = await get_best_model("hi there", intent="casual_chat")
    assert res1["chosen_model"] == normalize_model_id(KIMMI_CONVERSATIONAL)
    
    # Complex reasoning intent
    res2 = await get_best_model("prove fermat's theorem", intent="complex_reasoning")
    assert res2["chosen_model"] == normalize_model_id(DEEPSEEK_REASONING)
    
    # Code generation intent
    res3 = await get_best_model("write a sorting algorithm", intent="code_generation")
    assert res3["chosen_model"] == normalize_model_id(GROQ_CODE)
    
    # Summarization intent
    res4 = await get_best_model("summarize this document", intent="long_context_summary")
    assert res4["chosen_model"] == normalize_model_id(SUMMARIZER_MEMORY)


@pytest.mark.asyncio
async def test_execute_with_fallbacks_success():
    """Test fallback execution with success on primary."""
    chain = [
        normalize_model_id(KIMMI_CONVERSATIONAL),
        normalize_model_id(DEEPSEEK_REASONING),
    ]
    reply, used, fb = await execute_with_fallbacks(chain, "hello")
    assert used == chain[0]
    assert fb is False
    assert reply.startswith("[model:")


@pytest.mark.asyncio
async def test_execute_with_fallbacks_uses_backup():
    """Test fallback execution uses backup model."""
    chain = [
        "fail:" + normalize_model_id(KIMMI_CONVERSATIONAL),
        normalize_model_id(DEEPSEEK_REASONING),
    ]
    reply, used, fb = await execute_with_fallbacks(chain, "hello")
    assert used == normalize_model_id(DEEPSEEK_REASONING)
    assert fb is True
    assert reply.startswith("[model:")


def test_fallback_chain_simplified():
    """Test fallback chains are simplified to max 2 backups."""
    chain = build_fallback_chain(KIMMI_CONVERSATIONAL)
    assert len(chain) <= 3  # Primary + max 2 backups
    assert normalize_model_id(KIMMI_CONVERSATIONAL) in chain
    
    chain2 = build_fallback_chain(DEEPSEEK_REASONING)
    assert len(chain2) <= 3
    assert normalize_model_id(DEEPSEEK_REASONING) in chain2
