"""Skill Injection System for Kuro AI.

Loads modular skill definitions and injects specialized system prompts
based on user intent.

Features:
- JSON-based skill definitions (hot-reload capable)
- Keyword / regex trigger matching with configurable threshold
- Multiple skill chaining by priority
- Logging of applied skills
"""

from __future__ import annotations

import json
import re
import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SKILLS_FILE = Path(__file__).parent / "skills.json"

class Skill:
    def __init__(self, raw: Dict):
        self.name = raw.get("name")
        self.description = raw.get("description", "")
        self.priority = raw.get("priority", 0)
        self.trigger_patterns = raw.get("trigger_patterns", [])
        self.system_prompt = raw.get("system_prompt", "")
        self.allow_chain = raw.get("allow_chain", True)

    def match_score(self, text: str) -> int:
        score = 0
        lowered = text.lower()
        for pat in self.trigger_patterns:
            # Treat pattern as plain substring or simple regex if it contains meta chars
            if re.search(pat, lowered):
                score += 1
        return score

    def to_injection(self) -> str:
        return f"[SKILL:{self.name.upper()}]\n{self.system_prompt}".strip()

class SkillManager:
    def __init__(self, min_score: int = 1, max_chain: int = 3, auto_reload_seconds: int = 60):
        self.min_score = min_score
        self.max_chain = max_chain
        # Allow disabling periodic reload on constrained environments (e.g. Render free tier)
        if os.getenv("SKILL_AUTO_RELOAD_DISABLED") == "1":
            auto_reload_seconds = 10_000_000  # effectively never inside single process lifetime
            logger.info("Skill auto-reload disabled via SKILL_AUTO_RELOAD_DISABLED=1")
        self.auto_reload_seconds = auto_reload_seconds
        self._skills: List[Skill] = []
        self._last_load = 0.0
        self._last_mtime = 0.0
        self._load_skills(force=True)

    # ---------- Loading ----------
    def _load_skills(self, force: bool = False):
        try:
            stat = SKILLS_FILE.stat()
            if (not force and time.time() - self._last_load < self.auto_reload_seconds
                    and stat.st_mtime == self._last_mtime):
                return
            with SKILLS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._skills = [Skill(raw) for raw in data]
            self._skills.sort(key=lambda s: (-s.priority, s.name))
            self._last_load = time.time()
            self._last_mtime = stat.st_mtime
            logger.info(f"Loaded {len(self._skills)} skills (force={force})")
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")

    def reload_if_changed(self):
        # Fast path: If reload effectively disabled, skip stat call
        if self.auto_reload_seconds > 1_000_000:
            return
        self._load_skills(force=False)

    # ---------- Detection ----------
    def detect(self, user_text: str) -> List[Skill]:
        self.reload_if_changed()
        scores: List[Tuple[Skill, int]] = []
        for skill in self._skills:
            score = skill.match_score(user_text)
            if score >= self.min_score:
                scores.append((skill, score))
        # Sort by (skill priority, match score desc)
        scores.sort(key=lambda x: (-x[0].priority, -x[1]))
        selected: List[Skill] = []
        for skill, _ in scores:
            if selected and not selected[-1].allow_chain:
                break
            if len(selected) >= self.max_chain:
                break
            selected.append(skill)
            if not skill.allow_chain:
                break
        return selected

    # ---------- Injection ----------
    def build_injected_system_prompt(self, base_system: str, user_text: str) -> Tuple[str, List[str]]:
        skills = self.detect(user_text)
        if not skills:
            return base_system, []
        injection_blocks = [s.to_injection() for s in skills]
        merged = base_system + "\n\n" + "\n\n".join(injection_blocks)
        logger.info(f"Applied skills: {[s.name for s in skills]}")
        return merged, [s.name for s in skills]

# Global instance
skill_manager = SkillManager()
