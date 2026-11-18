"""Enhanced Skill System for Kuro AI.

Features:
- Structured JSON skill definitions with hot-reload
- Robust regex pattern matching with word boundaries and negative exclusions
- Direct alias resolution for frontend modes ('code', 'explain', 'creative', 'problem')
- Safe scoring logic: priority boosts apply ONLY to active pattern/keyword matches
- Explainable skill selection with debugging metadata
- Global singleton instance with backward compatibility
"""

from __future__ import annotations

import json
import re
import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, Any

logger = logging.getLogger(__name__)

SKILLS_FILE = Path(__file__).parent / "skills.json"


class Skill:
    def __init__(self, raw: Dict):
        self.id: str = raw.get("id") or raw.get("name", "unknown")
        self.name: str = raw.get("name") or self.id
        self.description: str = raw.get("description", "")
        self.priority: int = raw.get("priority", 0)
        self.trigger_patterns: List[str] = raw.get("trigger_patterns", [])
        self.negative_patterns: List[str] = raw.get("negative_patterns", [])
        self.system_prompt: str = raw.get("system_prompt", "")
        self.allow_chain: bool = raw.get("allow_chain", True)
        self.cooldown_seconds: int = raw.get("cooldown_seconds", 0)
        self.category: str = raw.get("category", "general")
        self.tags: List[str] = raw.get("tags", [])
        
        # Enhanced features
        self.regex_examples: List[str] = raw.get("regex_examples") or raw.get("embedding_examples", [])
        self.conflict_categories: Set[str] = set(raw.get("conflict_categories", []))
        self.quality_threshold: float = raw.get("quality_threshold", 0.7)
        self.intent_triggers: List[str] = raw.get("intent_triggers", [])
        self.keywords: List[str] = raw.get("keywords", [])
        
        # Pre-compile regex patterns for performance
        self._compiled_patterns: List[Tuple[str, re.Pattern]] = []
        self._compiled_negative: List[Tuple[str, re.Pattern]] = []
        self._compiled_examples: List[Tuple[str, re.Pattern]] = []
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns with word boundaries when needed."""
        try:
            for pattern in self.trigger_patterns:
                # If pattern is a plain phrase without regex anchors, enforce word boundaries
                if not any(char in pattern for char in [r"\b", "^", "$", "(", ")", "[", "]", "*", "+"]):
                    regex_str = r"\b" + re.escape(pattern.strip()) + r"\b"
                else:
                    regex_str = pattern
                self._compiled_patterns.append((pattern, re.compile(regex_str, re.IGNORECASE)))
            
            for pattern in self.negative_patterns:
                if not any(char in pattern for char in [r"\b", "^", "$", "(", ")", "[", "]"]):
                    regex_str = r"\b" + re.escape(pattern.strip()) + r"\b"
                else:
                    regex_str = pattern
                self._compiled_negative.append((pattern, re.compile(regex_str, re.IGNORECASE)))
            
            for example in self.regex_examples:
                escaped = re.escape(example.lower())
                flexible_pattern = r"\b" + escaped.replace(r"\ ", r"\s+").replace(r"\-", r"[-\s]*") + r"\b"
                self._compiled_examples.append((example, re.compile(flexible_pattern, re.IGNORECASE)))
        except re.error as e:
            logger.warning(f"Regex compilation error in skill {self.name}: {str(e)}")

    def match_regex(self, text: str) -> Tuple[float, List[str]]:
        """Regex-based pattern matching for skill triggers."""
        lowered = text.lower()
        score = 0.0
        reasons = []
        
        # Standard trigger patterns
        for raw_pat, comp in self._compiled_patterns:
            matches = comp.findall(text)
            if matches:
                match_count = len(matches)
                score += match_count * 1.0
                reasons.append(f"+pattern:{raw_pat}(matches={match_count})")
        
        # Negative patterns (exclusions)
        for raw_pat, comp in self._compiled_negative:
            if comp.search(lowered):
                score -= 2.0
                reasons.append(f"-pattern:{raw_pat}")
        
        return score, reasons
    
    def match_examples(self, text: str) -> Tuple[float, List[str]]:
        """Match against example queries."""
        if not self.regex_examples:
            return 0.0, []
        
        lowered = text.lower()
        max_score = 0.0
        best_example = ""
        reasons = []
        
        for example, compiled_pattern in self._compiled_examples:
            if compiled_pattern.search(lowered):
                score = 1.0
                example_words = set(example.lower().split())
                text_words = set(lowered.split())
                common_words = example_words.intersection(text_words)
                if common_words:
                    score += 0.5 * len(common_words) / max(len(example_words), 1)
                
                if score > max_score:
                    max_score = score
                    best_example = example
        
        if max_score > 0:
            reasons.append(f"example_match:{best_example}({max_score:.2f})")
        
        return max_score, reasons
    
    def match_keywords(self, text: str) -> Tuple[float, List[str]]:
        """Keyword matching with safe word boundary checks."""
        if not self.keywords:
            return 0.0, []
        
        lowered = text.lower()
        score = 0.0
        matched_keywords = []
        
        for keyword in self.keywords:
            kw_pat = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(kw_pat, lowered):
                score += 0.5
                matched_keywords.append(keyword)
        
        reasons = [f"keywords:{','.join(matched_keywords)}"] if matched_keywords else []
        return score, reasons
    
    def match_intents(self, detected_intents: Set[str]) -> Tuple[float, List[str]]:
        """Intent-based skill matching."""
        if not self.intent_triggers or not detected_intents:
            return 0.0, []
        
        matched_intents = [it for it in self.intent_triggers if it in detected_intents]
        if matched_intents:
            score = len(matched_intents) * 2.0
            reasons = [f"intent_match:{','.join(matched_intents)}"]
            return score, reasons
        
        return 0.0, []
    
    def calculate_total_score(self, text: str, detected_intents: Optional[Set[str]] = None) -> Tuple[float, List[str]]:
        """Calculate skill relevance score based purely on active matches."""
        total_score = 0.0
        all_reasons = []
        
        regex_score, regex_reasons = self.match_regex(text)
        total_score += regex_score
        all_reasons.extend(regex_reasons)
        
        example_score, example_reasons = self.match_examples(text)
        total_score += example_score
        all_reasons.extend(example_reasons)
        
        keyword_score, keyword_reasons = self.match_keywords(text)
        total_score += keyword_score
        all_reasons.extend(keyword_reasons)
        
        if detected_intents:
            intent_score, intent_reasons = self.match_intents(detected_intents)
            total_score += intent_score
            all_reasons.extend(intent_reasons)
        
        return total_score, all_reasons


class SkillManager:
    def __init__(self):
        self.skills: List[Skill] = []
        self._by_id: Dict[str, Skill] = {}
        self._by_name: Dict[str, Skill] = {}
        self._alias_map: Dict[str, str] = {
            # Code aliases
            "code": "code",
            "coding": "code",
            "developer": "code",
            "debugging": "code",
            "debug": "code",
            "programming": "code",
            # Explain aliases
            "explain": "explain",
            "explainer": "explain",
            "teaching": "explain",
            "teach": "explain",
            "tutorial": "explain",
            # Creative aliases
            "creative": "creative",
            "story": "creative",
            "storytelling": "creative",
            "brainstorming": "creative",
            "brainstorm": "creative",
            "writing": "creative",
            # Problem aliases
            "problem": "problem",
            "problem_solver": "problem",
            "math": "problem",
            "math_solver": "problem",
            "logic": "problem",
            # Utility aliases
            "creator": "creator_info",
            "creator_info": "creator_info",
            "summary": "summarizing",
            "summarizing": "summarizing",
            "summarize": "summarizing",
            "translation": "translation",
            "translate": "translation",
            "fact_check": "fact_check",
            "clarifier": "clarifier",
            "casual": "casual_chat",
            "farewell": "farewell_chat",
            "rewrite": "rewrite_tone",
        }
        self.last_reload = 0
        self._category_cooldowns: Dict[str, float] = {}
        self.load_skills()
    
    def load_skills(self):
        """Load skills from JSON with hot-reload support."""
        if not SKILLS_FILE.exists():
            logger.warning(f"Skills file not found: {SKILLS_FILE}")
            return
        
        try:
            stat = SKILLS_FILE.stat()
            if stat.st_mtime <= self.last_reload:
                return
            
            with open(SKILLS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            new_skills = []
            skill_list = data if isinstance(data, list) else data.get("skills", [])
            
            by_id = {}
            by_name = {}
            for skill_data in skill_list:
                try:
                    skill = Skill(skill_data)
                    new_skills.append(skill)
                    by_id[skill.id.lower()] = skill
                    by_name[skill.name.lower()] = skill
                except Exception as e:
                    logger.error(f"Failed to load skill {skill_data.get('name', 'unknown')}: {e}")
            
            self.skills = new_skills
            self._by_id = by_id
            self._by_name = by_name
            self.last_reload = stat.st_mtime
            logger.info(f"Loaded {len(self.skills)} skills from {SKILLS_FILE}")
            
        except Exception as e:
            logger.error(f"Failed to load skills file: {e}")
    
    def resolve_skill(self, skill_id_or_name: Optional[str], message: str) -> Optional[Skill]:
        """Resolve skill for a turn.
        
        - If skill_id_or_name is explicitly set (e.g. 'code', 'explain', 'creative', 'problem'),
          returns the matching skill immediately.
        - If 'auto', None, or empty, evaluates the user message for trigger patterns.
          Returns top skill if confident, or None for general natural conversation.
        """
        self.load_skills()
        
        if skill_id_or_name and skill_id_or_name.lower().strip() not in {"auto", "default", "none", ""}:
            clean_key = skill_id_or_name.lower().strip()
            target_id = self._alias_map.get(clean_key, clean_key)
            if target_id in self._by_id:
                return self._by_id[target_id]
            if target_id in self._by_name:
                return self._by_name[target_id]
            for s in self.skills:
                if s.id.lower() == clean_key or s.name.lower() == clean_key:
                    return s
        
        # Auto-detect from message content
        matches = self.select_skills(message, max_skills=1)
        if matches:
            top_skill, score, _ = matches[0]
            if score >= 1.0:
                return top_skill
        return None

    def select_skills(
        self,
        text: str,
        detected_intents: Optional[Set[str]] = None, 
        session_id: Optional[str] = None,
        max_skills: int = 3,
    ) -> List[Tuple[Skill, float, List[str]]]:
        """Select relevant skills based on regex patterns and intent matching."""
        self.load_skills()
        if not self.skills or not text or not text.strip():
            return []
        
        current_time = time.time()
        scored_skills = []
        
        preferred_skills = set()
        try:
            from routing.session_tracker import get_session_manager
            session_mgr = get_session_manager()
            preferred_skills = session_mgr.get_preferred_skills(session_id) if session_id else set()
        except Exception:
            pass
        
        for skill in self.skills:
            try:
                if self._is_category_on_cooldown(skill.category, current_time):
                    continue
                
                base_score, reasons = skill.calculate_total_score(text, detected_intents)
                
                # CRITICAL FIX: Only apply priority & preference boosts if the skill matched!
                # Zero-match skills should NEVER activate just because priority >= 7.
                if base_score <= 0.0:
                    continue
                
                score = base_score
                
                if skill.name in preferred_skills or skill.id in preferred_skills:
                    score += 0.5
                    reasons.append("session_preference(+0.5)")
                
                priority_bonus = skill.priority * 0.1
                score += priority_bonus
                reasons.append(f"priority_boost({priority_bonus:.1f})")
                
                if score >= skill.quality_threshold:
                    scored_skills.append((skill, score, reasons))
                    
            except Exception as e:
                logger.warning(f"Error scoring skill {skill.name}: {e}")
                continue
        
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        resolved_skills = self._resolve_conflicts(scored_skills)
        final_skills = self._apply_chaining_rules(resolved_skills, max_skills)
        
        return final_skills[:max_skills]
    
    def _is_category_on_cooldown(self, category: str, current_time: float) -> bool:
        if category in self._category_cooldowns:
            return current_time < self._category_cooldowns[category]
        return False
    
    def _resolve_conflicts(self, scored_skills: List[Tuple[Skill, float, List[str]]]) -> List[Tuple[Skill, float, List[str]]]:
        if not scored_skills:
            return []
        
        resolved = []
        used_categories = set()
        
        for skill, score, reasons in scored_skills:
            if skill.conflict_categories.intersection(used_categories):
                reasons.append(f"conflict_skip(categories={skill.conflict_categories})")
                continue
            
            resolved.append((skill, score, reasons))
            used_categories.add(skill.category)
            used_categories.update(skill.conflict_categories)
        
        return resolved
    
    def _apply_chaining_rules(self, skills: List[Tuple[Skill, float, List[str]]], max_skills: int) -> List[Tuple[Skill, float, List[str]]]:
        if not skills:
            return []
        
        final_skills = []
        for skill, score, reasons in skills:
            if len(final_skills) >= max_skills:
                break
            if not skill.allow_chain and final_skills:
                reasons.append("no_chain_skip")
                continue
            final_skills.append((skill, score, reasons))
        
        return final_skills
    
    def get_skill_prompts(self, skills: List[Tuple[Skill, float, List[str]]]) -> str:
        if not skills:
            return ""
        prompts = []
        for skill, score, reasons in skills:
            if skill.system_prompt.strip():
                prompts.append(f"# Active Skill: {skill.name.title()}\n{skill.system_prompt}")
        return "\n\n".join(prompts)
    
    def get_explanation(self, skills: List[Tuple[Skill, float, List[str]]]) -> str:
        if not skills:
            return "No skills selected"
        explanations = [f"{skill.name}(score={score:.1f})" for skill, score, _ in skills]
        return f"Selected skills: {'; '.join(explanations)}"
    
    def build_injected_system_prompt(
        self,
        base_system: str,
        user_text: str, 
        session_id: Optional[str] = None,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        start_time = time.time()
        
        detected_intents = set()
        try:
            from routing.regex_intent_detector import get_regex_intent_detector
            regex_detector = get_regex_intent_detector()
            detected_intents, _ = regex_detector.detect_intents(user_text)
        except Exception:
            pass
        
        selected_skills = self.select_skills(user_text, detected_intents, session_id)
        
        if not selected_skills:
            return base_system, [], {
                "selection_time_ms": (time.time() - start_time) * 1000,
                "skills_evaluated": len(self.skills),
                "skills_selected": 0,
                "detected_intents": list(detected_intents),
            }
        
        skill_prompts = self.get_skill_prompts(selected_skills)
        enhanced_system = base_system
        if skill_prompts:
            enhanced_system += "\n\n" + skill_prompts
        
        skill_names = [skill.name for skill, _, _ in selected_skills]
        metadata = {
            "selection_time_ms": (time.time() - start_time) * 1000,
            "skills_evaluated": len(self.skills),
            "skills_selected": len(selected_skills),
            "detected_intents": list(detected_intents),
            "selection_details": [
                {
                    "name": skill.name,
                    "category": skill.category,
                    "priority": skill.priority,
                    "score": score,
                    "reasons": reasons[:3],
                }
                for skill, score, reasons in selected_skills
            ],
        }
        return enhanced_system, skill_names, metadata


# Global singleton
_skill_manager = None

def get_skill_manager() -> SkillManager:
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager

skill_manager = get_skill_manager()
