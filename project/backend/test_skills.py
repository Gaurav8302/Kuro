"""Unit tests for SkillManager detection and injection."""

from skills.skill_manager import SkillManager, Skill


def test_skill_detection_single():
    mgr = SkillManager(min_score=1, max_chain=2, auto_reload_seconds=0)
    # Force load existing skills
    skills = mgr.detect("Can you summarize this article for me?")
    names = [s.name for s in skills]
    assert "summarizing" in names


def test_skill_chaining():
    mgr = SkillManager(min_score=1, max_chain=3, auto_reload_seconds=0)
    text = "Can you explain this python error and summarize the fix?"
    skills = mgr.detect(text)
    names = [s.name for s in skills]
    # teaching/coding/summarizing may trigger depending on patterns
    assert any(n in names for n in ["teaching", "coding"]) and "summarizing" in names


def test_injection_merging():
    mgr = SkillManager(min_score=1, max_chain=2, auto_reload_seconds=0)
    base = "BASE"  # simplified base system prompt
    merged, applied = mgr.build_injected_system_prompt(base, "Need ideas and options to brainstorm solutions")
    assert merged.startswith("BASE")
    assert applied, "Skills should be applied"
    assert any("brainstorming" == a for a in applied)
