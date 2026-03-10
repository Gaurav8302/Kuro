import json
import os
from pathlib import Path

os.environ['DISABLE_MEMORY_INIT'] = '1'

from orchestration.llm_orchestrator import _get_base_system_prompt
from routing.response_verifier import _is_browser_search_recommendation_only
from utils.kuro_prompt import build_system_instruction


def test_browser_search_recommendation_only_helper_is_strict():
    disclaimer_only = (
        "My knowledge may be outdated on this topic. "
        "You can enable browser search for the latest information."
    )
    mixed_answer = (
        "The United Kingdom does not have a president. "
        "My knowledge may be outdated on this topic. "
        "You can enable browser search for the latest information."
    )

    assert _is_browser_search_recommendation_only(disclaimer_only) is True
    assert _is_browser_search_recommendation_only(mixed_answer) is False


def test_orchestrator_uses_canonical_conversation_prompt_by_default():
    assert _get_base_system_prompt() == build_system_instruction("conversation")


def test_skill_prompts_do_not_use_conflicting_absolute_name_rules():
    skills_path = Path(__file__).parent / "skills" / "skills.json"
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    prompts = {skill["name"]: skill["system_prompt"] for skill in skills}

    assert "ALWAYS greet them by name" not in prompts["casual_chat"]
    assert "ALWAYS use their name" not in prompts["farewell_chat"]
    assert "Ask 2-3 specific clarifying questions" not in prompts["clarifier"]
    assert "apparent interests" not in prompts["creator_info"]