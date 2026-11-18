"""Lightweight Skill Injection System Proxy.

This module proxies to the unified `backend.skills.skill_manager`.
"""

from skills.skill_manager import (
    Skill,
    SkillManager,
    get_skill_manager,
    skill_manager,
    SKILLS_FILE,
)

__all__ = [
    "Skill",
    "SkillManager",
    "get_skill_manager",
    "skill_manager",
    "SKILLS_FILE",
]
