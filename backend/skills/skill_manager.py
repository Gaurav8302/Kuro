"""Enhanced Skill Injection System for Kuro AI.

Features:
- JSON-based skill definitions with hot-reload
- Hybrid trigger matching (regex + embeddings)
- Adaptive priorities based on session usage
- Contextual cooldowns and category exclusions
- Explainable skill selection with reasoning
- Advanced chaining control and conflict resolution

Enhanced capabilities:
- Session-aware skill adaptation
- Embedding-based semantic matching
- Dynamic priority adjustments
- Context-aware cooldown logic
"""

from __future__ import annotations

import json
import re
import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from routing.embedding_similarity import get_embedding_similarity
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
        
        # Enhanced features
        self.embedding_examples: List[str] = raw.get("embedding_examples", [])
        self.conflict_categories: Set[str] = set(raw.get("conflict_categories", []))
        self.quality_threshold: float = raw.get("quality_threshold", 0.7)
        
        # Precompile regex patterns
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

    def match_regex(self, text: str) -> Tuple[int, List[str]]:
        """Regex-based pattern matching."""
        lowered = text.lower()
        score = 0
        reasons: List[str] = []
        
        for raw_pat, comp in self._compiled:
            if comp.search(lowered):
                score += 1
                reasons.append(f"+regex:{raw_pat}")
        
        for raw_pat, comp in self._compiled_negative:
            if comp.search(lowered):
                score -= 1
                reasons.append(f"-regex:{raw_pat}")
        
        return score, reasons
    
    def match_embedding(self, text: str) -> Tuple[float, List[str]]:
        """Embedding-based semantic matching."""
        if not self.embedding_examples:
            return 0.0, []
        
        embedding_sim = get_embedding_similarity()
        if embedding_sim.model is None:
            return 0.0, ["embedding_unavailable"]
        
        max_similarity = 0.0
        best_example = ""
        
        for example in self.embedding_examples:
            similarity = embedding_sim.compute_similarity(text, example)
            if similarity > max_similarity:
                max_similarity = similarity
                best_example = example
        
        reasons = []
        if max_similarity > embedding_sim.similarity_threshold:
            reasons.append(f"+embedding:{best_example}={max_similarity:.2f}")
        
        return max_similarity, reasons
    
    def match(self, text: str, session_id: Optional[str] = None) -> Tuple[float, List[str]]:
        """Enhanced matching combining regex and embeddings with session adaptation."""
        # Get base regex score
        regex_score, regex_reasons = self.match_regex(text)
        
        # Get embedding score
        embedding_score, embedding_reasons = self.match_embedding(text)
        
        # Combine scores with weighting
        if embedding_score > 0:
            # Embedding match found, weight it higher
            combined_score = regex_score * 0.3 + embedding_score * 0.7
        else:
            # No embedding match, rely on regex
            combined_score = float(regex_score)
        
        # Session-based priority adjustment
        session_boost = 0.0
        if session_id:
            session_manager = get_session_manager()
            session = session_manager.get_session(session_id)
            session_boost = session.get_skill_priority_boost(self.name)
            if session_boost > 0:
                combined_score += session_boost
                regex_reasons.append(f"+session_boost:{session_boost:.1f}")
        
        all_reasons = regex_reasons + embedding_reasons
        return combined_score, all_reasons

    def to_injection(self) -> str:
        header = f"[SKILL:{self.name.upper()}|cat={self.category}|prio={self.priority}]"
        return f"{header}\n{self.system_prompt}".strip()

class SkillManager:
    def __init__(self, min_score: float = 1.0, max_chain: int = 3, auto_reload_seconds: int = 60):
        self.min_score = float(os.getenv("SKILL_MIN_SCORE", str(min_score)))
        self.max_chain = int(os.getenv("SKILL_MAX_CHAIN", str(max_chain)))
        
        # Allow disabling periodic reload on constrained environments
        if os.getenv("SKILL_AUTO_RELOAD_DISABLED") == "1":
            auto_reload_seconds = 10_000_000  # effectively never
            logger.info("Skill auto-reload disabled via SKILL_AUTO_RELOAD_DISABLED=1")
        
        self.auto_reload_seconds = auto_reload_seconds
        self.debug = os.getenv("SKILL_DEBUG") == "1"
        self._skills: List[Skill] = []
        self._last_load = 0.0
        self._last_mtime = 0.0
        self._last_applied: Dict[str, float] = {}
        
        # Enhanced features
        self._embedding_cache: Dict[str, List[Tuple[str, float]]] = {}
        self._session_manager = get_session_manager()
        
        self._load_skills(force=True)

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
            
            # Clear embedding cache when skills reload
            self._embedding_cache.clear()
            
            logger.info(f"Loaded {len(self._skills)} skills (force={force})")
            
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")

    def reload_if_changed(self):
        # Fast path: If reload effectively disabled, skip stat call
        if self.auto_reload_seconds > 1_000_000:
            return
        self._load_skills(force=False)

    def detect(self, user_text: str, session_id: Optional[str] = None) -> List[Skill]:
        """Detect applicable skills using enhanced matching."""
        return [s for s, _, _ in self.detect_with_explanations(user_text, session_id)]

    def detect_with_explanations(self, user_text: str, session_id: Optional[str] = None) -> List[Tuple[Skill, float, List[str]]]:
        """Enhanced skill detection with session awareness and conflict resolution."""
        self.reload_if_changed()
        
        evaluations: List[Tuple[Skill, float, List[str]]] = []
        now = time.time()
        
        # Get session context for adaptive behavior
        session_adaptations = {}
        if session_id:
            session = self._session_manager.get_session(session_id)
            session_adaptations = self._session_manager.get_skill_adaptations(session_id)
        
        # Evaluate each skill
        for skill in self._skills:
            score, reasons = skill.match(user_text, session_id)
            
            if score < self.min_score:
                continue
            
            # Enhanced cooldown check (contextual)
            if skill.cooldown_seconds > 0:
                last_used = self._last_applied.get(skill.name, 0.0)
                time_since_last = now - last_used
                
                # Apply contextual cooldown logic
                if session_id and 'contextual_cooldown_check' in session_adaptations:
                    cooldown_func = session_adaptations['contextual_cooldown_check']
                    if cooldown_func(skill.name, skill.cooldown_seconds):
                        remaining = skill.cooldown_seconds - time_since_last
                        reasons.append(f"contextual_cooldown({int(remaining)}s)")
                        continue
                elif time_since_last < skill.cooldown_seconds:
                    remaining = skill.cooldown_seconds - time_since_last
                    reasons.append(f"cooldown({int(remaining)}s)")
                    continue
            
            evaluations.append((skill, score, reasons))
        
        # Sort by priority desc, then score desc
        evaluations.sort(key=lambda x: (-x[0].priority, -x[1]))
        
        # Advanced chaining control with conflict resolution
        selected: List[Tuple[Skill, float, List[str]]] = []
        used_categories: Set[str] = set()
        category_exclusions = session_adaptations.get('category_exclusions', set())
        
        for skill, score, reasons in evaluations:
            # Check category exclusions
            if skill.category in category_exclusions:
                if self.debug:
                    reasons.append(f"category_excluded:{skill.category}")
                continue
            
            # Check for conflicts with already selected skills
            if skill.conflict_categories.intersection(used_categories):
                conflicts = skill.conflict_categories.intersection(used_categories)
                if self.debug:
                    reasons.append(f"category_conflict:{','.join(conflicts)}")
                continue
            
            # Check chaining limits
            if selected and not selected[-1][0].allow_chain:
                if self.debug:
                    reasons.append("chain_blocked_by_previous")
                break
            
            if len(selected) >= self.max_chain:
                if self.debug:
                    reasons.append("max_chain_reached")
                break
            
            # Select this skill
            selected.append((skill, score, reasons))
            used_categories.add(skill.category)
            self._last_applied[skill.name] = now
            
            # Record usage in session
            if session_id:
                self._session_manager.record_skill_usage(session_id, [skill.name])
            
            # Check if this skill blocks further chaining
            if not skill.allow_chain:
                if self.debug:
                    reasons.append("chain_blocked_by_current")
                break
        
        # Log selection for debugging
        if self.debug and selected:
            debug_info = [
                f"{s.name}:score={score:.1f}:reasons={reasons}"
                for s, score, reasons in selected
            ]
            logger.info("Enhanced skill selection: " + " | ".join(debug_info))
        
        return selected

    def build_injected_system_prompt(self, base_system: str, user_text: str, 
                                   session_id: Optional[str] = None) -> Tuple[str, List[str], Dict[str, any]]:
        """Build enhanced system prompt with detailed metadata.
        
        Returns:
            Tuple of (enhanced_prompt, skill_names, metadata)
            
        For backwards compatibility, when called with 2 return values expected,
        returns (enhanced_prompt, skill_names) without metadata.
        """
        start_time = time.time()
        
        detected = self.detect_with_explanations(user_text, session_id)
        
        if not detected:
            base_result = (base_system, [], {'selection_time_ms': (time.time() - start_time) * 1000})
            return base_result
        
        skills = [d[0] for d in detected]
        injection_blocks = [s.to_injection() for s in skills]
        merged = base_system + "\n\n" + "\n\n".join(injection_blocks)
        
        # Build detailed metadata
        metadata = {
            'selection_time_ms': (time.time() - start_time) * 1000,
            'skills_evaluated': len(self._skills),
            'skills_selected': len(skills),
            'total_score': sum(score for _, score, _ in detected),
            'selection_details': [
                {
                    'name': skill.name,
                    'category': skill.category,
                    'priority': skill.priority,
                    'score': score,
                    'reasons': reasons
                }
                for skill, score, reasons in detected
            ],
            'session_id': session_id
        }
        
        skill_names = [s.name for s in skills]
        
        if self.debug:
            logger.info(f"Applied {len(skills)} skills in {metadata['selection_time_ms']:.1f}ms: {skill_names}")
        else:
            logger.info(f"Applied skills: {skill_names}")
        
        return merged, skill_names, metadata
    
    def build_injected_system_prompt_legacy(self, base_system: str, user_text: str) -> Tuple[str, List[str]]:
        """Legacy method for backwards compatibility - returns only prompt and skill names."""
        enhanced_prompt, skill_names, _ = self.build_injected_system_prompt(base_system, user_text, None)
        return enhanced_prompt, skill_names

# Global instance
skill_manager = SkillManager()
