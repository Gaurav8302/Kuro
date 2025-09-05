"""Lightweight Skill Injection System for Kuro AI.

Features:
- JSON-based skill definitions with hot-reload
- Comprehensive regex pattern matching
- Adaptive priorities based on session usage (lightweight)
- Contextual cooldowns and category exclusions
- Explainable skill selection with reasoning
- Advanced chaining control and conflict resolution

Replaced heavy embedding-based matching with robust regex patterns
for optimal performance on resource-constrained servers.
"""

from __future__ import annotations

import json
import re
import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, Any
from routing.regex_intent_detector import get_regex_intent_detector
from routing.session_tracker import get_session_manager

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
        
        # Enhanced features (regex-based instead of embedding-based)
        self.regex_examples: List[str] = raw.get("regex_examples", [])  # Renamed from embedding_examples
        self.conflict_categories: Set[str] = set(raw.get("conflict_categories", []))
        self.quality_threshold: float = raw.get("quality_threshold", 0.7)
        self.intent_triggers: List[str] = raw.get("intent_triggers", [])  # Intent-based triggers
        self.keywords: List[str] = raw.get("keywords", [])  # Simple keyword matching
        
        # Pre-compile regex patterns for performance
        self._compiled_patterns = []
        self._compiled_negative = []
        self._compiled_examples = []
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        try:
            for pattern in self.trigger_patterns:
                self._compiled_patterns.append((pattern, re.compile(pattern, re.IGNORECASE)))
            
            for pattern in self.negative_patterns:
                self._compiled_negative.append((pattern, re.compile(pattern, re.IGNORECASE)))
            
            for example in self.regex_examples:
                # Convert examples to flexible regex patterns
                escaped = re.escape(example.lower())
                # Allow some variation in word boundaries and optional words
                flexible_pattern = escaped.replace('\\ ', '\\s+').replace('\\-', '[-\\s]*')
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
                score += len(matches)  # Multiple matches boost score
                reasons.append(f"+pattern:{raw_pat}(matches={len(matches)})")
        
        # Negative patterns (exclusions)
        for raw_pat, comp in self._compiled_negative:
            if comp.search(lowered):
                score -= 2.0  # Strong penalty for negative matches
                reasons.append(f"-pattern:{raw_pat}")
        
        return score, reasons
    
    def match_examples(self, text: str) -> Tuple[float, List[str]]:
        """Match against regex examples (lightweight alternative to embeddings)."""
        if not self.regex_examples:
            return 0.0, []
        
        lowered = text.lower()
        max_score = 0.0
        best_example = ""
        reasons = []
        
        for example, compiled_pattern in self._compiled_examples:
            if compiled_pattern.search(lowered):
                # Simple scoring based on pattern match strength
                score = 1.0
                
                # Bonus for exact keyword matches
                example_words = set(example.lower().split())
                text_words = set(lowered.split())
                common_words = example_words.intersection(text_words)
                if common_words:
                    score += 0.5 * len(common_words) / len(example_words)
                
                if score > max_score:
                    max_score = score
                    best_example = example
        
        if max_score > 0:
            reasons.append(f"example_match:{best_example}({max_score:.2f})")
        
        return max_score, reasons
    
    def match_keywords(self, text: str) -> Tuple[float, List[str]]:
        """Simple keyword-based matching."""
        if not self.keywords:
            return 0.0, []
        
        lowered = text.lower()
        score = 0.0
        matched_keywords = []
        
        for keyword in self.keywords:
            if keyword.lower() in lowered:
                score += 0.5
                matched_keywords.append(keyword)
        
        reasons = [f"keywords:{','.join(matched_keywords)}"] if matched_keywords else []
        return score, reasons
    
    def match_intents(self, detected_intents: Set[str]) -> Tuple[float, List[str]]:
        """Intent-based skill matching."""
        if not self.intent_triggers or not detected_intents:
            return 0.0, []
        
        matched_intents = []
        for intent_trigger in self.intent_triggers:
            if intent_trigger in detected_intents:
                matched_intents.append(intent_trigger)
        
        if matched_intents:
            score = len(matched_intents) * 2.0  # Strong bonus for intent matches
            reasons = [f"intent_match:{','.join(matched_intents)}"]
            return score, reasons
        
        return 0.0, []
    
    def calculate_total_score(self, text: str, detected_intents: Optional[Set[str]] = None) -> Tuple[float, List[str]]:
        """Calculate total skill relevance score using all matching methods."""
        total_score = 0.0
        all_reasons = []
        
        # Regex pattern matching
        regex_score, regex_reasons = self.match_regex(text)
        total_score += regex_score
        all_reasons.extend(regex_reasons)
        
        # Example-based matching (regex alternative to embeddings)
        example_score, example_reasons = self.match_examples(text)
        total_score += example_score
        all_reasons.extend(example_reasons)
        
        # Keyword matching
        keyword_score, keyword_reasons = self.match_keywords(text)
        total_score += keyword_score
        all_reasons.extend(keyword_reasons)
        
        # Intent-based matching
        if detected_intents:
            intent_score, intent_reasons = self.match_intents(detected_intents)
            total_score += intent_score
            all_reasons.extend(intent_reasons)
        
        return total_score, all_reasons

class SkillManager:
    def __init__(self):
        self.skills: List[Skill] = []
        self.last_reload = 0
        self._skill_usage_history = {}  # Simple in-memory tracking
        self._category_cooldowns = {}  # Category-based cooldowns
        self.load_skills()
    
    def load_skills(self):
        """Load skills from JSON with hot-reload support."""
        if not SKILLS_FILE.exists():
            logger.warning(f"Skills file not found: {SKILLS_FILE}")
            return
        
        try:
            stat = SKILLS_FILE.stat()
            if stat.st_mtime <= self.last_reload:
                return  # No changes since last reload
            
            with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.skills = []
            # Handle both array format and object format
            skill_list = data if isinstance(data, list) else data.get("skills", [])
            
            for skill_data in skill_list:
                try:
                    skill = Skill(skill_data)
                    self.skills.append(skill)
                except Exception as e:
                    logger.error(f"Failed to load skill {skill_data.get('name', 'unknown')}: {str(e)}")
            
            self.last_reload = stat.st_mtime
            logger.info(f"Loaded {len(self.skills)} skills from {SKILLS_FILE}")
            
        except Exception as e:
            logger.error(f"Failed to load skills file: {str(e)}")
    
    def select_skills(self, text: str, detected_intents: Optional[Set[str]] = None, 
                     session_id: Optional[str] = None, max_skills: int = 3) -> List[Tuple[Skill, float, List[str]]]:
        """Select relevant skills based on regex patterns and intent matching."""
        self.load_skills()  # Hot-reload check
        
        if not self.skills:
            return []
        
        current_time = time.time()
        scored_skills = []
        
        # Get session preferences for lightweight adaptation
        session_mgr = get_session_manager()
        preferred_skills = session_mgr.get_preferred_skills(session_id) if session_id else set()
        
        for skill in self.skills:
            try:
                # Check category cooldown
                if self._is_category_on_cooldown(skill.category, current_time):
                    continue
                
                # Calculate skill relevance score
                score, reasons = skill.calculate_total_score(text, detected_intents)
                
                # Session preference boost (lightweight)
                if skill.name in preferred_skills:
                    score += 1.0
                    reasons.append("session_preference(+1.0)")
                
                # Priority adjustment
                score += skill.priority * 0.1
                if skill.priority > 0:
                    reasons.append(f"priority_boost({skill.priority * 0.1:.1f})")
                
                # Only include skills that meet minimum threshold
                if score >= skill.quality_threshold:
                    scored_skills.append((skill, score, reasons))
                    
            except Exception as e:
                logger.warning(f"Error scoring skill {skill.name}: {str(e)}")
                continue
        
        # Sort by score and apply conflict resolution
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        resolved_skills = self._resolve_conflicts(scored_skills)
        
        # Apply chaining rules and limits
        final_skills = self._apply_chaining_rules(resolved_skills, max_skills)
        
        # Update usage tracking
        if session_id and final_skills:
            for skill, _, _ in final_skills:
                session_mgr.record_skill_usage(session_id, skill.name)
        
        return final_skills[:max_skills]
    
    def _is_category_on_cooldown(self, category: str, current_time: float) -> bool:
        """Check if a skill category is on cooldown."""
        if category in self._category_cooldowns:
            return current_time < self._category_cooldowns[category]
        return False
    
    def _resolve_conflicts(self, scored_skills: List[Tuple[Skill, float, List[str]]]) -> List[Tuple[Skill, float, List[str]]]:
        """Resolve category conflicts between skills."""
        if not scored_skills:
            return []
        
        resolved = []
        used_categories = set()
        
        for skill, score, reasons in scored_skills:
            # Check for category conflicts
            if skill.conflict_categories.intersection(used_categories):
                reasons.append(f"conflict_skip(categories={skill.conflict_categories})")
                continue
            
            resolved.append((skill, score, reasons))
            used_categories.add(skill.category)
            
            # Add conflict categories to prevent future conflicts
            used_categories.update(skill.conflict_categories)
        
        return resolved
    
    def _apply_chaining_rules(self, skills: List[Tuple[Skill, float, List[str]]], max_skills: int) -> List[Tuple[Skill, float, List[str]]]:
        """Apply skill chaining rules and limits."""
        if not skills:
            return []
        
        final_skills = []
        
        for skill, score, reasons in skills:
            if len(final_skills) >= max_skills:
                break
            
            # Check if skill allows chaining
            if not skill.allow_chain and final_skills:
                reasons.append("no_chain_skip")
                continue
            
            final_skills.append((skill, score, reasons))
        
        return final_skills
    
    def get_skill_prompts(self, skills: List[Tuple[Skill, float, List[str]]]) -> str:
        """Generate combined system prompt from selected skills."""
        if not skills:
            return ""
        
        prompts = []
        for skill, score, reasons in skills:
            if skill.system_prompt.strip():
                prompts.append(f"# {skill.name.title()}\n{skill.system_prompt}")
        
        return "\n\n".join(prompts)
    
    def get_explanation(self, skills: List[Tuple[Skill, float, List[str]]]) -> str:
        """Generate explanation of skill selection."""
        if not skills:
            return "No skills selected"
        
        explanations = []
        for skill, score, reasons in skills:
            reason_str = ", ".join(reasons[:3])  # Limit for readability
            explanations.append(f"{skill.name}(score={score:.1f}, {reason_str})")
        
        return f"Selected skills: {'; '.join(explanations)}"
    
    def build_injected_system_prompt(self, base_system: str, user_text: str, 
                                   session_id: Optional[str] = None) -> Tuple[str, List[str], Dict[str, Any]]:
        """Build enhanced system prompt with skill injection and metadata.
        
        Args:
            base_system: Base system prompt
            user_text: User message text
            session_id: Session ID for adaptive behavior
            
        Returns:
            Tuple of (enhanced_prompt, skill_names, metadata)
        """
        start_time = time.time()
        
        # Detect intents first
        regex_detector = get_regex_intent_detector()
        detected_intents, _ = regex_detector.detect_intents(user_text)
        
        # Select skills
        selected_skills = self.select_skills(user_text, detected_intents, session_id)
        
        if not selected_skills:
            return base_system, [], {
                'selection_time_ms': (time.time() - start_time) * 1000,
                'skills_evaluated': len(self.skills),
                'skills_selected': 0,
                'detected_intents': list(detected_intents)
            }
        
        # Build enhanced prompt
        skill_prompts = self.get_skill_prompts(selected_skills)
        enhanced_system = base_system
        if skill_prompts:
            enhanced_system += "\n\n" + skill_prompts
        
        # Get skill names
        skill_names = [skill.name for skill, _, _ in selected_skills]
        
        # Build metadata
        metadata = {
            'selection_time_ms': (time.time() - start_time) * 1000,
            'skills_evaluated': len(self.skills),
            'skills_selected': len(selected_skills),
            'detected_intents': list(detected_intents),
            'selection_details': [
                {
                    'name': skill.name,
                    'category': skill.category,
                    'priority': skill.priority,
                    'score': score,
                    'reasons': reasons[:3]  # Limit for readability
                }
                for skill, score, reasons in selected_skills
            ]
        }
        
        return enhanced_system, skill_names, metadata

# Global skill manager instance
_skill_manager = None

def get_skill_manager() -> SkillManager:
    """Get global skill manager instance (singleton)."""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager

# Global instance for backward compatibility
skill_manager = get_skill_manager()
