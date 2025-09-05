"""Session-based tracking for adaptive skill priorities and contextual behavior.

Maintains per-session state to improve skill selection and routing decisions
based on user patterns and interaction history.
"""
from __future__ import annotations
import time
import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class SessionContext:
    """Contextual information for a user session."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # Skill usage tracking
    skill_usage_count: Dict[str, int] = field(default_factory=dict)
    skill_last_used: Dict[str, float] = field(default_factory=dict)
    recent_skills: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # Intent tracking
    intent_history: deque = field(default_factory=lambda: deque(maxlen=20))
    intent_frequency: Dict[str, int] = field(default_factory=dict)
    
    # Model performance tracking for this session
    model_preferences: Dict[str, float] = field(default_factory=dict)
    model_failures: Dict[str, int] = field(default_factory=dict)
    
    # Context-aware cooldowns
    contextual_cooldowns: Dict[str, float] = field(default_factory=dict)
    
    # Conversation patterns
    query_complexity_trend: deque = field(default_factory=lambda: deque(maxlen=5))
    response_satisfaction: deque = field(default_factory=lambda: deque(maxlen=10))
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if session has expired."""
        return time.time() - self.last_activity > timeout_seconds
    
    def get_skill_priority_boost(self, skill_name: str) -> float:
        """Get priority boost for a skill based on session usage."""
        usage_count = self.skill_usage_count.get(skill_name, 0)
        
        # More frequently used skills get higher boost
        if usage_count >= 5:
            return 2.0  # Strong boost for heavily used skills
        elif usage_count >= 2:
            return 1.0  # Moderate boost
        elif usage_count == 1:
            return 0.5  # Small boost for tried skills
        else:
            return 0.0  # No boost for unused skills
    
    def should_apply_contextual_cooldown(self, skill_name: str, base_cooldown: int) -> bool:
        """Determine if contextual cooldown should be applied."""
        now = time.time()
        
        # Check if skill was used very recently
        last_used = self.skill_last_used.get(skill_name, 0)
        time_since_last = now - last_used
        
        # Dynamic cooldown based on context
        if skill_name in ['storytelling', 'creative_writing']:
            # Creative skills need longer cooldowns to avoid repetition
            dynamic_cooldown = max(base_cooldown, 300)  # At least 5 minutes
        elif skill_name in ['debugging', 'code_analysis']:
            # Debugging can repeat quickly if new errors appear
            dynamic_cooldown = base_cooldown * 0.5
        elif skill_name in ['casual_chat', 'greeting']:
            # Casual skills can repeat more frequently
            dynamic_cooldown = base_cooldown * 0.3
        else:
            dynamic_cooldown = base_cooldown
        
        return time_since_last < dynamic_cooldown
    
    def record_skill_usage(self, skill_name: str):
        """Record that a skill was used."""
        now = time.time()
        self.skill_usage_count[skill_name] = self.skill_usage_count.get(skill_name, 0) + 1
        self.skill_last_used[skill_name] = now
        self.recent_skills.append((skill_name, now))
        self.update_activity()
    
    def record_intent(self, intent: str):
        """Record an intent classification."""
        self.intent_history.append((intent, time.time()))
        self.intent_frequency[intent] = self.intent_frequency.get(intent, 0) + 1
        self.update_activity()
    
    def record_model_performance(self, model_id: str, success: bool, latency_ms: float):
        """Record model performance for session-specific preferences."""
        if success:
            # Successful responses improve model preference
            current_pref = self.model_preferences.get(model_id, 0.5)
            self.model_preferences[model_id] = min(1.0, current_pref + 0.1)
            
            # Factor in latency - faster responses are preferred
            if latency_ms < 1000:  # Under 1 second
                self.model_preferences[model_id] = min(1.0, self.model_preferences[model_id] + 0.05)
        else:
            # Failures reduce preference and increase failure count
            self.model_failures[model_id] = self.model_failures.get(model_id, 0) + 1
            current_pref = self.model_preferences.get(model_id, 0.5)
            self.model_preferences[model_id] = max(0.0, current_pref - 0.2)
        
        self.update_activity()
    
    def get_model_preference_score(self, model_id: str) -> float:
        """Get preference score for a model (0.0 to 1.0)."""
        base_score = self.model_preferences.get(model_id, 0.5)
        failure_count = self.model_failures.get(model_id, 0)
        
        # Penalize models with recent failures
        if failure_count > 0:
            penalty = min(0.3, failure_count * 0.1)
            base_score = max(0.0, base_score - penalty)
        
        return base_score
    
    def detect_conversation_pattern(self) -> str:
        """Analyze recent interaction patterns."""
        if len(self.intent_history) < 3:
            return "exploratory"
        
        recent_intents = [intent for intent, _ in list(self.intent_history)[-5:]]
        
        # Check for focused patterns
        if len(set(recent_intents)) <= 2:
            return "focused"  # User is focused on specific topics
        elif 'complex_reasoning' in recent_intents and 'teaching' in recent_intents:
            return "learning"  # User is in learning mode
        elif 'casual_chat' in recent_intents and len(set(recent_intents)) > 3:
            return "exploratory"  # User is exploring various topics
        else:
            return "mixed"
    
    def get_category_exclusions(self) -> Set[str]:
        """Get skill categories to avoid based on recent usage."""
        exclusions = set()
        
        # If user just used creative skills, avoid more creative skills for a bit
        recent_skill_names = [skill for skill, _ in list(self.recent_skills)[-3:]]
        
        creative_skills = {'storytelling', 'creative_writing', 'brainstorming'}
        analytical_skills = {'debugging', 'fact_check', 'analysis'}
        
        if any(skill in creative_skills for skill in recent_skill_names):
            if len([s for s in recent_skill_names if s in creative_skills]) >= 2:
                exclusions.add('creative')
        
        if any(skill in analytical_skills for skill in recent_skill_names):
            if len([s for s in recent_skill_names if s in analytical_skills]) >= 2:
                exclusions.add('analytical')
        
        return exclusions


class SessionManager:
    """Manages user sessions and contextual behavior tracking."""
    
    def __init__(self, session_timeout: int = 3600, cleanup_interval: int = 1800):
        """Initialize session manager.
        
        Args:
            session_timeout: Session expiry time in seconds (default: 1 hour)
            cleanup_interval: How often to clean expired sessions in seconds
        """
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
    
    def get_session(self, session_id: str) -> SessionContext:
        """Get or create a session context."""
        with self._lock:
            # Periodic cleanup
            if time.time() - self._last_cleanup > self.cleanup_interval:
                self._cleanup_expired_sessions()
            
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(session_id)
                logger.debug(f"Created new session: {session_id}")
            
            session = self._sessions[session_id]
            session.update_activity()
            return session
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        expired_sessions = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(self.session_timeout)
        ]
        
        for sid in expired_sessions:
            del self._sessions[sid]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        self._last_cleanup = time.time()
    
    def record_skill_usage(self, session_id: str, skill_names: List[str]):
        """Record skill usage for a session."""
        session = self.get_session(session_id)
        for skill_name in skill_names:
            session.record_skill_usage(skill_name)
    
    def record_intent(self, session_id: str, intent: str):
        """Record intent classification for a session."""
        session = self.get_session(session_id)
        session.record_intent(intent)
    
    def record_model_performance(self, session_id: str, model_id: str, 
                               success: bool, latency_ms: float):
        """Record model performance for a session."""
        session = self.get_session(session_id)
        session.record_model_performance(model_id, success, latency_ms)
    
    def get_skill_adaptations(self, session_id: str) -> Dict[str, any]:
        """Get skill system adaptations for a session."""
        session = self.get_session(session_id)
        
        return {
            'priority_boosts': {
                skill: session.get_skill_priority_boost(skill)
                for skill in session.skill_usage_count.keys()
            },
            'category_exclusions': session.get_category_exclusions(),
            'conversation_pattern': session.detect_conversation_pattern(),
            'contextual_cooldown_check': session.should_apply_contextual_cooldown
        }
    
    def get_routing_adaptations(self, session_id: str) -> Dict[str, any]:
        """Get routing system adaptations for a session."""
        session = self.get_session(session_id)
        
        return {
            'model_preferences': session.model_preferences,
            'model_failures': session.model_failures,
            'preference_score_func': session.get_model_preference_score,
            'conversation_pattern': session.detect_conversation_pattern()
        }
    
    def get_session_stats(self) -> Dict[str, any]:
        """Get overall session statistics."""
        with self._lock:
            active_sessions = len(self._sessions)
            total_skills_used = sum(
                len(session.skill_usage_count) for session in self._sessions.values()
            )
            
            return {
                'active_sessions': active_sessions,
                'total_skills_used': total_skills_used,
                'avg_skills_per_session': total_skills_used / max(1, active_sessions)
            }


# Global singleton instance
_session_manager = None
_init_lock = threading.Lock()

def get_session_manager() -> SessionManager:
    """Get global session manager instance (singleton)."""
    global _session_manager
    
    if _session_manager is None:
        with _init_lock:
            if _session_manager is None:
                _session_manager = SessionManager()
    
    return _session_manager
