"""Comprehensive Test Suite for Skills System & Browser Web Search Integration."""

import pytest
import unittest.mock as mock
from skills.skill_manager import SkillManager, get_skill_manager, Skill
from tools.web_search import (
    detect_search_need,
    search_web,
    format_search_results_for_prompt,
    _search_duckduckgo_wikipedia,
)
from llm.prompts import PromptBuilder
from memory.chat_manager_v3 import ChatManagerV3


def test_skills_json_loading_and_frontend_mappings():
    """Verify all frontend and backend skills are loaded and aliased properly."""
    sm = SkillManager()
    assert len(sm.skills) >= 10, f"Expected at least 10 skills, got {len(sm.skills)}"

    # Frontend explicit modes
    skill_code = sm.resolve_skill("code", "")
    assert skill_code is not None
    assert skill_code.id == "code"
    assert skill_code.name == "code_developer"

    skill_explain = sm.resolve_skill("explain", "")
    assert skill_explain is not None
    assert skill_explain.id == "explain"
    assert skill_explain.name == "deep_explainer"

    skill_creative = sm.resolve_skill("creative", "")
    assert skill_creative is not None
    assert skill_creative.id == "creative"
    assert skill_creative.name == "creative_mind"

    skill_problem = sm.resolve_skill("problem", "")
    assert skill_problem is not None
    assert skill_problem.id == "problem"
    assert skill_problem.name == "problem_solver"

    # Legacy aliases
    assert sm.resolve_skill("debugging", "").id == "code"
    assert sm.resolve_skill("teaching", "").id == "explain"
    assert sm.resolve_skill("storytelling", "").id == "creative"
    assert sm.resolve_skill("math_solver", "").id == "problem"
    assert sm.resolve_skill("creator_info", "").id == "creator_info"


def test_no_false_positive_regex_and_priority_boost():
    """Verify the critical bug fix: zero-match queries must NEVER trigger high priority skills,

    and 'hi' must not match inside 'this' or 'think'.
    """
    sm = SkillManager()

    # Query containing "this" should NOT match "casual_chat" ("hi" inside "this")
    res_this = sm.select_skills("this is a simple message about architecture")
    assert not any(s.name == "casual_chat" for s, _, _ in res_this), "False positive: 'hi' inside 'this' triggered casual_chat"

    # General neutral message with 0 matches should NOT match fact_check or casual_chat
    res_zero = sm.select_skills("we went to the grocery store yesterday to buy apples and bread")
    assert len(res_zero) == 0, f"Zero match query triggered skills: {[s.name for s, _, _ in res_zero]}"

    # Auto resolution on generic conversation should return None
    assert sm.resolve_skill("auto", "we went to the grocery store yesterday") is None


def test_auto_skill_detection():
    """Verify accurate detection of skills when skill='auto'."""
    sm = SkillManager()

    # Code detection
    s_code = sm.resolve_skill("auto", "I am getting a TypeError exception traceback in my python async function")
    assert s_code is not None
    assert s_code.id == "code"

    # Explain detection
    s_explain = sm.resolve_skill("auto", "Explain how quantum computing works and give me an analogy")
    assert s_explain is not None
    assert s_explain.id == "explain"

    # Creative detection
    s_creative = sm.resolve_skill("auto", "Write a sci-fi story about a rogue time traveler and an AI")
    assert s_creative is not None
    assert s_creative.id == "creative"

    # Problem detection
    s_problem = sm.resolve_skill("auto", "Solve this calculus integral and equation step by step")
    assert s_problem is not None
    assert s_problem.id == "problem"

    # Creator info
    s_creator = sm.resolve_skill("auto", "Who created you and tell me about Gaurav")
    assert s_creator is not None
    assert s_creator.id == "creator_info"


def test_search_need_detection():
    """Verify regex patterns for detecting queries requiring live web search."""
    assert detect_search_need("Search the web for latest release of Python") is True
    assert detect_search_need("What is the current stock price of Apple today?") is True
    assert detect_search_need("Who won the match yesterday?") is True
    assert detect_search_need("What is today's weather in San Francisco?") is True
    assert detect_search_need("Check out https://github.com/python/cpython") is True

    # Standard conversational or coding queries do not need live search
    assert detect_search_need("How do I write a binary search algorithm in Python?") is False
    assert detect_search_need("Tell me a funny joke about cats") is False
    assert detect_search_need("Hello there Kuro, how are you?") is False


@pytest.mark.asyncio
async def test_web_search_multi_provider_fallbacks():
    """Verify multi-tier web search cascade and structured result format."""
    # 1. Tavily mock
    mock_tavily = [
        {"title": "Python 3.14 Highlights", "url": "https://python.org/3.14", "content": "Python 3.14 includes JIT improvements."}
    ]
    with mock.patch("os.getenv", side_effect=lambda k, d="": "mock-tavily-key" if k == "TAVILY_API_KEY" else ""):
        with mock.patch("tools.web_search._search_tavily", return_value=[{
            "title": "Python 3.14 Highlights",
            "url": "https://python.org/3.14",
            "snippet": "Python 3.14 includes JIT improvements.",
            "source": "tavily"
        }]):
            res = await search_web("Python 3.14 release", max_results=3)
            assert res["provider"] == "tavily"
            assert res["has_results"] is True
            assert len(res["results"]) == 1
            assert res["results"][0]["url"] == "https://python.org/3.14"

    # 2. Zero-config fallback mock
    with mock.patch("os.getenv", return_value=""):
        mock_fallback_results = [
            {"title": "OpenAI GPT-4o", "url": "https://en.wikipedia.org/wiki/GPT-4o", "snippet": "Multimodal LLM", "source": "wikipedia"}
        ]
        with mock.patch("tools.web_search._search_duckduckgo_wikipedia", return_value=mock_fallback_results):
            res_fallback = await search_web("OpenAI GPT-4o", max_results=2)
            assert res_fallback["provider"] == "duckduckgo_wikipedia"
            assert res_fallback["has_results"] is True
            assert res_fallback["results"][0]["title"] == "OpenAI GPT-4o"


def test_format_search_results_for_prompt():
    """Verify formatting search results with source citations into prompt markdown."""
    search_data = {
        "query": "Kuro AI companion",
        "provider": "duckduckgo_wikipedia",
        "has_results": True,
        "results": [
            {
                "title": "Kuro AI Official",
                "url": "https://kuro.ai",
                "snippet": "Kuro is an intelligent conversational AI assistant.",
                "source": "duckduckgo"
            },
            {
                "title": "Artificial Companion",
                "url": "https://en.wikipedia.org/wiki/Companion",
                "snippet": "Companionship technology overview.",
                "source": "wikipedia"
            }
        ]
    }
    formatted = format_search_results_for_prompt(search_data)
    assert "Live Web Search Results" in formatted
    assert "[1] Kuro AI Official" in formatted
    assert "https://kuro.ai" in formatted
    assert "[Source Title](URL)" in formatted


def test_prompt_builder_with_skills_and_search():
    """Verify PromptBuilder incorporates both active skill instructions and live web context."""
    pb = PromptBuilder()
    sm = SkillManager()
    active_skill = sm.resolve_skill("code", "")

    search_data = {
        "query": "FastAPI async testing",
        "provider": "live_web",
        "has_results": True,
        "results": [
            {"title": "FastAPI Docs", "url": "https://fastapi.tiangolo.com/tutorial", "snippet": "Async testing guide"}
        ]
    }

    prompt = pb.build(
        user_input="How do I write an async test with httpx in FastAPI?",
        chat_history=[{"role": "user", "content": "hi"}],
        active_skill=active_skill,
        search_results=search_data,
    )

    assert "Active Skill Mode (Code Developer):" in prompt
    assert "You are in CODE DEVELOPER mode." in prompt
    assert "Live Web Search Results" in prompt
    assert "https://fastapi.tiangolo.com/tutorial" in prompt


@pytest.mark.asyncio
async def test_chat_manager_v3_skills_and_search_integration():
    """Test full turn in ChatManagerV3 with skill selection and web search flags."""
    cm = ChatManagerV3()

    # Mock response generation to avoid external API calls in unit test
    async def mock_generate(prompt, model_type="conversation"):
        return f"Response generated for {model_type} with prompt length {len(prompt)}"

    cm._generate_response = mock_generate
    cm._analyze_intent = mock.AsyncMock(return_value={"intent": "general", "needs_memory": False, "memory_types": []})
    cm.memory_controller.decide = mock.AsyncMock(return_value={"use_memory": False, "types": [], "top_k": 0})
    cm.memory_updater.process = mock.AsyncMock(return_value=None)

    with mock.patch("memory.user_profile.get_user_profile", return_value={"name": "Test User"}), \
         mock.patch("db.mongo.get_active_user_facts", return_value=[]):
        # 1. Test explicit skill override
        turn1 = await cm.handle_chat(
            user_id="test_user_skills",
            session_id="session_skills_1",
            user_input="How do I fix this recursion limit error in Python?",
            chat_history=[],
            skill="code",
            search_mode=False,
        )
        assert turn1["active_skill"] == "code"
        assert turn1["route_rule"] == "v3_code"

        # 2. Test forced search mode
        mock_search_results = {
            "query": "Latest Mars Rover news",
            "provider": "duckduckgo",
            "has_results": True,
            "results": [{"title": "Perseverance Update", "url": "https://nasa.gov/mars", "snippet": "New sample cached."}]
        }
        with mock.patch("tools.web_search.search_web", return_value=mock_search_results):
            turn2 = await cm.handle_chat(
                user_id="test_user_skills",
                session_id="session_skills_2",
                user_input="What is the latest news from the Mars Rover?",
                chat_history=[],
                skill="auto",
                search_mode=True,
            )
            assert turn2["search_mode"] is True
            assert turn2["search_results"] is not None
            assert turn2["search_results"]["has_results"] is True

        # 3. Test suggest_search flag when search_mode is False but query needs search
        turn3 = await cm.handle_chat(
            user_id="test_user_skills",
            session_id="session_skills_3",
            user_input="What is today's stock price of Nvidia?",
            chat_history=[],
            skill="auto",
            search_mode=False,
        )
        assert turn3["suggest_search"] is True
