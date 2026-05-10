"""
Skill Router — Rule-Based Skill Matching

Matches user input to the most relevant skill using keyword
and regex scoring. No LLM calls — pure deterministic matching.

Scoring formula:
  score = keyword_hits * 0.5
        + pattern_hits * 1.5
        - negative_hits * 3.0
        + priority_boost
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from skills.base import SkillDefinition
from skills.registry import SkillRegistry, get_skill_registry

logger = logging.getLogger(__name__)


class SkillRouter:
    """Rule-based skill matcher with cooldown management."""

    # Minimum score to consider a skill match
    MATCH_THRESHOLD = 0.5

    def __init__(self, registry: Optional[SkillRegistry] = None):
        self.registry = registry or get_skill_registry()
        # Cooldown tracking: {skill_name: last_used_timestamp}
        self._cooldowns: Dict[str, float] = {}

    def match(
        self,
        user_input: str,
        intent: Optional[str] = None,
        top_k: int = 1,
    ) -> Optional[SkillDefinition]:
        """Match user input to the best skill.

        Args:
            user_input: The user's message.
            intent: Optional intent classification (from intent classifier).
            top_k: Number of top candidates to consider (returns best).

        Returns:
            Best matching SkillDefinition or None.
        """
        candidates = self._score_all(user_input, intent)
        if not candidates:
            return None

        # Return the highest-scored skill
        return candidates[0][0]

    def match_multi(
        self,
        user_input: str,
        intent: Optional[str] = None,
        top_k: int = 3,
    ) -> List[SkillDefinition]:
        """Match user input to multiple skills (for chaining)."""
        candidates = self._score_all(user_input, intent)
        return [skill for skill, _ in candidates[:top_k]]

    def _score_all(
        self,
        user_input: str,
        intent: Optional[str] = None,
    ) -> List[Tuple[SkillDefinition, float]]:
        """Score all skills against user input."""
        query = (user_input or "").lower().strip()
        now = time.time()
        candidates: List[Tuple[SkillDefinition, float]] = []

        for skill in self.registry.skills:
            # Check cooldown
            if skill.cooldown_seconds > 0:
                last_used = self._cooldowns.get(skill.name, 0)
                if now - last_used < skill.cooldown_seconds:
                    continue

            score = self._score_skill(skill, query, intent)
            if score >= self.MATCH_THRESHOLD:
                candidates.append((skill, score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def _score_skill(
        self,
        skill: SkillDefinition,
        query: str,
        intent: Optional[str] = None,
    ) -> float:
        """Score a single skill against query."""
        score = 0.0

        # Keyword matching (fast substring check)
        for kw in skill.keywords:
            if kw.lower() in query:
                score += 0.5

        # Trigger pattern matching (regex)
        for pattern in skill._compiled_triggers:
            if pattern.search(query):
                score += 1.5

        # Negative pattern penalty
        for pattern in skill._compiled_negative:
            if pattern.search(query):
                score -= 3.0

        # Priority boost (0-10 priority mapped to 0-0.5 boost)
        score += skill.priority * 0.05

        # Category-intent alignment bonus
        if intent and skill.category:
            _INTENT_CATEGORY_MAP = {
                "code": "analytical",
                "debugging": "analytical",
                "reasoning": "analytical",
                "creative": "creative",
                "greeting": "social",
            }
            expected_category = _INTENT_CATEGORY_MAP.get(intent)
            if expected_category == skill.category:
                score += 0.5

        return score

    def mark_used(self, skill_name: str) -> None:
        """Record that a skill was just used (for cooldown tracking)."""
        self._cooldowns[skill_name] = time.time()

    def get_system_prompt(self, skill: Optional[SkillDefinition]) -> str:
        """Get the system prompt for a matched skill."""
        if skill and skill.system_prompt:
            return skill.system_prompt
        return ""
