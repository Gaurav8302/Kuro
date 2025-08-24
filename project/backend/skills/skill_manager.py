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
        self.name: str = raw.get("name")
        self.description: str = raw.get("description", "")
        self.priority: int = raw.get("priority", 0)
        self.trigger_patterns: List[str] = raw.get("trigger_patterns", [])
        self.negative_patterns: List[str] = raw.get("negative_patterns", [])
        self.system_prompt: str = raw.get("system_prompt", "")
        self.allow_chain: bool = raw.get("allow_chain", True)
        self.cooldown_seconds: int = raw.get("cooldown_seconds", 0)
        self.category: str = raw.get("category", "general")
        self.tags: List[str] = raw.get("tags", [])
        # Precompile patterns for efficiency & clarity
        self._compiled: List[Tuple[str, re.Pattern]] = [
            (p, self._compile_pattern(p)) for p in self.trigger_patterns
        ]
        self._compiled_negative: List[Tuple[str, re.Pattern]] = [
            (p, self._compile_pattern(p)) for p in self.negative_patterns
        ]

    @staticmethod
    def _compile_pattern(pat: str) -> re.Pattern:
        # Allow explicit regex via prefix 're:' or presence of common meta characters
        if pat.startswith('re:'):
            raw = pat[3:]
            return re.compile(raw, re.IGNORECASE)
        meta_chars = set('.^$*+?{}[]|()')
        if any(ch in meta_chars for ch in pat):
            return re.compile(pat, re.IGNORECASE)
        # Plain substring pattern -> escape & compile
        return re.compile(re.escape(pat.lower()))

    def match(self, text: str) -> Tuple[int, List[str]]:
        """Return (score, reasons). Score counts positive pattern hits minus negatives.
        Reasons list shows which patterns matched / blocked for transparency."""
        lowered = text.lower()
        score = 0
        reasons: List[str] = []
        for raw_pat, comp in self._compiled:
            if comp.search(lowered):
                score += 1
                reasons.append(f"+{raw_pat}")
        for raw_pat, comp in self._compiled_negative:
            if comp.search(lowered):
                score -= 1
                reasons.append(f"-{raw_pat}")
        return score, reasons

    def to_injection(self) -> str:
        header = f"[SKILL:{self.name.upper()}|cat={self.category}|prio={self.priority}]"
        return f"{header}\n{self.system_prompt}".strip()

class SkillManager:
    def __init__(self, min_score: int = 1, max_chain: int = 3, auto_reload_seconds: int = 60):
        self.min_score = int(os.getenv("SKILL_MIN_SCORE", str(min_score)))
        self.max_chain = int(os.getenv("SKILL_MAX_CHAIN", str(max_chain)))
        # Allow disabling periodic reload on constrained environments (e.g. Render free tier)
        if os.getenv("SKILL_AUTO_RELOAD_DISABLED") == "1":
            auto_reload_seconds = 10_000_000  # effectively never inside single process lifetime
            logger.info("Skill auto-reload disabled via SKILL_AUTO_RELOAD_DISABLED=1")
        self.auto_reload_seconds = auto_reload_seconds
        self.debug = os.getenv("SKILL_DEBUG") == "1"
        self._skills: List[Skill] = []
        self._last_load = 0.0
        self._last_mtime = 0.0
        self._last_applied: Dict[str, float] = {}
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
        return [s for s, _, _ in self.detect_with_explanations(user_text)]

    def detect_with_explanations(self, user_text: str) -> List[Tuple[Skill, int, List[str]]]:
        """Return list of (skill, score, reasons) after applying scoring, cooldown, chaining."""
        self.reload_if_changed()
        evaluations: List[Tuple[Skill, int, List[str]]] = []
        now = time.time()
        for skill in self._skills:
            score, reasons = skill.match(user_text)
            if score < self.min_score:
                continue
            # Cooldown check
            if skill.cooldown_seconds > 0:
                last = self._last_applied.get(skill.name, 0.0)
                if now - last < skill.cooldown_seconds:
                    if self.debug:
                        reasons.append(f"cooldown({int(skill.cooldown_seconds - (now - last))}s)")
                    continue
            evaluations.append((skill, score, reasons))
        # Sort by (priority desc, score desc)
        evaluations.sort(key=lambda x: (-x[0].priority, -x[1]))
        selected: List[Tuple[Skill, int, List[str]]] = []
        for skill, score, reasons in evaluations:
            if selected and not selected[-1][0].allow_chain:
                break
            if len(selected) >= self.max_chain:
                break
            selected.append((skill, score, reasons))
            self._last_applied[skill.name] = now
            if not skill.allow_chain:
                break
        return selected

    # ---------- Injection ----------
    def build_injected_system_prompt(self, base_system: str, user_text: str) -> Tuple[str, List[str]]:
        detected = self.detect_with_explanations(user_text)
        if not detected:
            return base_system, []
        skills = [d[0] for d in detected]
        injection_blocks = [s.to_injection() for s in skills]
        merged = base_system + "\n\n" + "\n\n".join(injection_blocks)
        if self.debug:
            debug_table = [f"{s.name}: score={score} reasons={reasons}" for s, score, reasons in detected]
            logger.info("Skill debug => " + " | ".join(debug_table))
        logger.info(f"Applied skills: {[s.name for s in skills]}")
        return merged, [s.name for s in skills]

# Global instance
skill_manager = SkillManager()
