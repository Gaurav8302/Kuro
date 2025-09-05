"""Lightweight session-based tracking for adaptive behavior.

Simple in-memory tracking without heavy ML dependencies.
Maintains basic user preferences and patterns for improved routing.
"""
from __future__ import annotations
import time
import logging
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

class LightweightSessionManager:
    """Simple session tracking for user preferences and patterns."""
    
    def __init__(self, session_timeout: int = 3600):
        self._sessions = {}
        self._session_timeout = session_timeout
        self._lock = threading.RLock()
        
    def _get_session(self, session_id: str) -> Dict:
        """Get or create session data."""
        current_time = time.time()
        
        with self._lock:
            # Clean expired sessions
            expired_sessions = [
                sid for sid, data in self._sessions.items()
                if current_time - data.get('last_activity', 0) > self._session_timeout
            ]
            for sid in expired_sessions:
                del self._sessions[sid]
            
            # Get or create session
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    'created_at': current_time,
                    'last_activity': current_time,
                    'skill_usage': defaultdict(int),
                    'model_preferences': defaultdict(float),
                    'intent_history': deque(maxlen=10),
                    'recent_skills': deque(maxlen=5),
                    'model_successes': defaultdict(int),
                    'model_failures': defaultdict(int),
                }
            
            # Update activity
            self._sessions[session_id]['last_activity'] = current_time
            return self._sessions[session_id]
    
    def record_skill_usage(self, session_id: str, skill_name: str):
        """Record skill usage for session adaptation."""
        if not session_id:
            return
            
        session = self._get_session(session_id)
        session['skill_usage'][skill_name] += 1
        session['recent_skills'].append(skill_name)
        
        logger.debug(f"Recorded skill usage: {session_id} -> {skill_name}")
    
    def record_intent(self, session_id: str, intent: str):
        """Record intent for pattern tracking."""
        if not session_id or not intent:
            return
            
        session = self._get_session(session_id)
        session['intent_history'].append(intent)
    
    def record_model_result(self, session_id: str, model_id: str, success: bool):
        """Record model performance for session preferences."""
        if not session_id:
            return
            
        session = self._get_session(session_id)
        if success:
            session['model_successes'][model_id] += 1
            session['model_preferences'][model_id] += 0.1
        else:
            session['model_failures'][model_id] += 1
            session['model_preferences'][model_id] -= 0.2
    
    def get_preferred_skills(self, session_id: str) -> Set[str]:
        """Get frequently used skills for this session."""
        if not session_id:
            return set()
        
        session = self._get_session(session_id)
        skill_usage = session['skill_usage']
        
        # Return skills used more than once
        preferred = {skill for skill, count in skill_usage.items() if count > 1}
        return preferred
    
    def get_preferred_models(self, session_id: str) -> Set[str]:
        """Get models with positive preference scores."""
        if not session_id:
            return set()
        
        session = self._get_session(session_id)
        preferences = session['model_preferences']
        
        # Return models with positive preference scores
        preferred = {model for model, score in preferences.items() if score > 0.1}
        return preferred
    
    def get_recent_intents(self, session_id: str) -> List[str]:
        """Get recent intents for context awareness."""
        if not session_id:
            return []
        
        session = self._get_session(session_id)
        return list(session['intent_history'])
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get session statistics for debugging."""
        if not session_id:
            return {}
        
        session = self._get_session(session_id)
        return {
            'created_at': session['created_at'],
            'last_activity': session['last_activity'],
            'skill_count': len(session['skill_usage']),
            'total_interactions': sum(session['skill_usage'].values()),
            'preferred_skills': list(self.get_preferred_skills(session_id)),
            'preferred_models': list(self.get_preferred_models(session_id)),
            'recent_intents': list(session['intent_history'])[-3:],  # Last 3
        }
    
    def cleanup_expired_sessions(self):
        """Manual cleanup of expired sessions."""
        current_time = time.time()
        
        with self._lock:
            expired_sessions = [
                sid for sid, data in self._sessions.items()
                if current_time - data.get('last_activity', 0) > self._session_timeout
            ]
            
            for sid in expired_sessions:
                del self._sessions[sid]
                
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        self.cleanup_expired_sessions()
        return len(self._sessions)

# Global singleton
_session_manager = None
_manager_lock = threading.Lock()

def get_session_manager() -> LightweightSessionManager:
    """Get global session manager (singleton)."""
    global _session_manager
    if _session_manager is None:
        with _manager_lock:
            if _session_manager is None:
                _session_manager = LightweightSessionManager()
    return _session_manager
