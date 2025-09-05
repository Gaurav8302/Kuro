"""Structured logging for explainable AI routing and skill selection decisions.

Provides detailed, queryable logs for debugging and optimization of the
routing and skill selection systems.
"""
from __future__ import annotations
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Structured data for a routing decision."""
    timestamp: float
    session_id: Optional[str]
    query: str
    query_length: int
    context_tokens: int
    
    # Intent detection
    detected_intents: List[str]
    intent_detection_method: str
    intent_explanations: List[str]
    
    # Model selection
    selected_model: str
    selection_method: str
    selection_reason: str
    confidence: float
    
    # Alternatives considered
    alternatives: List[Dict[str, Any]]
    
    # Performance metrics
    routing_latency_ms: float
    
    # Additional context
    metadata: Dict[str, Any]


@dataclass
class SkillSelection:
    """Structured data for skill selection."""
    timestamp: float
    session_id: Optional[str]
    query: str
    query_length: int
    
    # Skills evaluated and selected
    skills_evaluated: int
    skills_selected: int
    selected_skills: List[str]
    
    # Selection details
    selection_details: List[Dict[str, Any]]
    
    # Session adaptations applied
    session_adaptations: Dict[str, Any]
    
    # Performance metrics
    selection_latency_ms: float
    
    # Total scores and reasoning
    total_skill_score: float
    
    # Additional metadata
    metadata: Dict[str, Any]


@dataclass
class FallbackEvent:
    """Structured data for fallback routing events."""
    timestamp: float
    session_id: Optional[str]
    original_model: str
    fallback_model: str
    fallback_reason: str
    fallback_trigger: str
    latency_ms: Optional[float]
    success: bool
    error_details: Optional[str]


class ExplainableLogger:
    """Centralized logging for routing and skill decisions with structured output."""
    
    def __init__(self, log_file: str = "routing_decisions.jsonl", max_memory_entries: int = 1000):
        self.log_file = Path(__file__).parent.parent / "logs" / log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory circular buffer for recent decisions (for real-time analysis)
        self._memory_buffer: deque = deque(maxlen=max_memory_entries)
        self._lock = threading.Lock()
        
        # Statistics tracking
        self._stats = {
            'total_routing_decisions': 0,
            'total_skill_selections': 0,
            'total_fallback_events': 0,
            'session_count': set(),
            'model_usage': {},
            'skill_usage': {},
            'fallback_reasons': {},
        }
    
    def log_routing_decision(self, decision: RoutingDecision):
        """Log a routing decision with structured data."""
        with self._lock:
            # Add to memory buffer
            decision_dict = asdict(decision)
            decision_dict['event_type'] = 'routing_decision'
            self._memory_buffer.append(decision_dict)
            
            # Update statistics
            self._stats['total_routing_decisions'] += 1
            if decision.session_id:
                self._stats['session_count'].add(decision.session_id)
            
            model_usage = self._stats['model_usage']
            model_usage[decision.selected_model] = model_usage.get(decision.selected_model, 0) + 1
            
            # Write to file
            self._write_to_file(decision_dict)
            
            # Log summary for immediate visibility
            intent_str = ','.join(decision.detected_intents)
            logger.info(
                f"ROUTING: intent={intent_str} query_len={decision.query_length} "
                f"chosen_model={decision.selected_model} method={decision.selection_method} "
                f"confidence={decision.confidence:.2f} latency={decision.routing_latency_ms:.1f}ms "
                f"session={decision.session_id}"
            )
    
    def log_skill_selection(self, selection: SkillSelection):
        """Log a skill selection with structured data."""
        with self._lock:
            # Add to memory buffer
            selection_dict = asdict(selection)
            selection_dict['event_type'] = 'skill_selection'
            self._memory_buffer.append(selection_dict)
            
            # Update statistics
            self._stats['total_skill_selections'] += 1
            if selection.session_id:
                self._stats['session_count'].add(selection.session_id)
            
            skill_usage = self._stats['skill_usage']
            for skill in selection.selected_skills:
                skill_usage[skill] = skill_usage.get(skill, 0) + 1
            
            # Write to file
            self._write_to_file(selection_dict)
            
            # Log summary for immediate visibility
            skills_str = ','.join(selection.selected_skills)
            logger.info(
                f"SKILLS: query_len={selection.query_length} selected={len(selection.selected_skills)} "
                f"skills=[{skills_str}] total_score={selection.total_skill_score:.1f} "
                f"latency={selection.selection_latency_ms:.1f}ms session={selection.session_id}"
            )
    
    def log_fallback_event(self, fallback: FallbackEvent):
        """Log a fallback routing event."""
        with self._lock:
            # Add to memory buffer
            fallback_dict = asdict(fallback)
            fallback_dict['event_type'] = 'fallback_event'
            self._memory_buffer.append(fallback_dict)
            
            # Update statistics
            self._stats['total_fallback_events'] += 1
            if fallback.session_id:
                self._stats['session_count'].add(fallback.session_id)
            
            fallback_reasons = self._stats['fallback_reasons']
            fallback_reasons[fallback.fallback_reason] = fallback_reasons.get(fallback.fallback_reason, 0) + 1
            
            # Write to file
            self._write_to_file(fallback_dict)
            
            # Log summary for immediate visibility
            logger.warning(
                f"FALLBACK: {fallback.original_model} -> {fallback.fallback_model} "
                f"reason={fallback.fallback_reason} trigger={fallback.fallback_trigger} "
                f"success={fallback.success} session={fallback.session_id}"
            )
    
    def _write_to_file(self, data: Dict[str, Any]):
        """Write structured data to JSONL file."""
        try:
            with self.log_file.open('a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to write to routing log file: {str(e)}")
    
    def get_recent_decisions(self, count: int = 100, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent decisions from memory buffer."""
        with self._lock:
            decisions = list(self._memory_buffer)
            
            if event_type:
                decisions = [d for d in decisions if d.get('event_type') == event_type]
            
            return decisions[-count:] if count > 0 else decisions
    
    def get_session_decisions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all decisions for a specific session."""
        with self._lock:
            return [d for d in self._memory_buffer if d.get('session_id') == session_id]
    
    def get_model_performance_summary(self) -> Dict[str, Any]:
        """Get summary of model performance from recent decisions."""
        with self._lock:
            routing_decisions = [d for d in self._memory_buffer if d.get('event_type') == 'routing_decision']
            
            model_stats = {}
            for decision in routing_decisions:
                model = decision.get('selected_model')
                if model:
                    if model not in model_stats:
                        model_stats[model] = {
                            'total_selections': 0,
                            'avg_confidence': 0.0,
                            'avg_latency': 0.0,
                            'selection_methods': {}
                        }
                    
                    stats = model_stats[model]
                    stats['total_selections'] += 1
                    
                    # Update running averages
                    confidence = decision.get('confidence', 0.0)
                    latency = decision.get('routing_latency_ms', 0.0)
                    
                    n = stats['total_selections']
                    stats['avg_confidence'] = ((n - 1) * stats['avg_confidence'] + confidence) / n
                    stats['avg_latency'] = ((n - 1) * stats['avg_latency'] + latency) / n
                    
                    # Track selection methods
                    method = decision.get('selection_method', 'unknown')
                    methods = stats['selection_methods']
                    methods[method] = methods.get(method, 0) + 1
            
            return model_stats
    
    def get_skill_usage_summary(self) -> Dict[str, Any]:
        """Get summary of skill usage patterns."""
        with self._lock:
            skill_selections = [d for d in self._memory_buffer if d.get('event_type') == 'skill_selection']
            
            skill_stats = {}
            for selection in skill_selections:
                selected_skills = selection.get('selected_skills', [])
                
                for skill in selected_skills:
                    if skill not in skill_stats:
                        skill_stats[skill] = {
                            'total_selections': 0,
                            'avg_score': 0.0,
                            'co_occurrences': {}
                        }
                    
                    skill_stats[skill]['total_selections'] += 1
                    
                    # Track co-occurring skills
                    for other_skill in selected_skills:
                        if other_skill != skill:
                            cooccur = skill_stats[skill]['co_occurrences']
                            cooccur[other_skill] = cooccur.get(other_skill, 0) + 1
            
            return skill_stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats['session_count'] = len(stats['session_count'])
            stats['memory_buffer_size'] = len(self._memory_buffer)
            stats['log_file_path'] = str(self.log_file)
            return stats
    
    def analyze_routing_patterns(self, time_window_hours: float = 24.0) -> Dict[str, Any]:
        """Analyze routing patterns over a time window."""
        cutoff_time = time.time() - (time_window_hours * 3600)
        
        with self._lock:
            recent_decisions = [
                d for d in self._memory_buffer
                if d.get('timestamp', 0) > cutoff_time and d.get('event_type') == 'routing_decision'
            ]
            
            if not recent_decisions:
                return {'error': 'No recent decisions found'}
            
            # Analyze patterns
            intent_patterns = {}
            model_confidence = {}
            selection_methods = {}
            
            for decision in recent_decisions:
                # Intent patterns
                intents = decision.get('detected_intents', [])
                for intent in intents:
                    intent_patterns[intent] = intent_patterns.get(intent, 0) + 1
                
                # Model confidence distribution
                model = decision.get('selected_model')
                confidence = decision.get('confidence', 0.0)
                if model:
                    if model not in model_confidence:
                        model_confidence[model] = []
                    model_confidence[model].append(confidence)
                
                # Selection methods
                method = decision.get('selection_method', 'unknown')
                selection_methods[method] = selection_methods.get(method, 0) + 1
            
            # Calculate averages for model confidence
            model_avg_confidence = {
                model: sum(confidences) / len(confidences)
                for model, confidences in model_confidence.items()
            }
            
            return {
                'time_window_hours': time_window_hours,
                'total_decisions': len(recent_decisions),
                'intent_distribution': intent_patterns,
                'model_avg_confidence': model_avg_confidence,
                'selection_method_distribution': selection_methods,
                'unique_sessions': len(set(d.get('session_id') for d in recent_decisions if d.get('session_id')))
            }


# Global singleton instance
_explainable_logger = None
_init_lock = threading.Lock()

def get_explainable_logger() -> ExplainableLogger:
    """Get global explainable logger instance (singleton)."""
    global _explainable_logger
    
    if _explainable_logger is None:
        with _init_lock:
            if _explainable_logger is None:
                _explainable_logger = ExplainableLogger()
    
    return _explainable_logger


# Convenience functions for common logging patterns
def log_routing_decision(query: str, selected_model: str, intents: List[str], 
                        confidence: float, session_id: Optional[str] = None,
                        **kwargs) -> None:
    """Quick logging of routing decision."""
    decision = RoutingDecision(
        timestamp=time.time(),
        session_id=session_id,
        query=query[:200],  # Truncate for privacy/size
        query_length=len(query),
        context_tokens=kwargs.get('context_tokens', 0),
        detected_intents=intents,
        intent_detection_method=kwargs.get('intent_detection_method', 'unknown'),
        intent_explanations=kwargs.get('intent_explanations', []),
        selected_model=selected_model,
        selection_method=kwargs.get('selection_method', 'unknown'),
        selection_reason=kwargs.get('selection_reason', ''),
        confidence=confidence,
        alternatives=kwargs.get('alternatives', []),
        routing_latency_ms=kwargs.get('routing_latency_ms', 0.0),
        metadata=kwargs.get('metadata', {})
    )
    
    get_explainable_logger().log_routing_decision(decision)


def log_skill_selection(query: str, selected_skills: List[str], 
                       session_id: Optional[str] = None, **kwargs) -> None:
    """Quick logging of skill selection."""
    selection = SkillSelection(
        timestamp=time.time(),
        session_id=session_id,
        query=query[:200],  # Truncate for privacy/size
        query_length=len(query),
        skills_evaluated=kwargs.get('skills_evaluated', 0),
        skills_selected=len(selected_skills),
        selected_skills=selected_skills,
        selection_details=kwargs.get('selection_details', []),
        session_adaptations=kwargs.get('session_adaptations', {}),
        selection_latency_ms=kwargs.get('selection_latency_ms', 0.0),
        total_skill_score=kwargs.get('total_skill_score', 0.0),
        metadata=kwargs.get('metadata', {})
    )
    
    get_explainable_logger().log_skill_selection(selection)


def log_fallback_event(original_model: str, fallback_model: str, reason: str,
                      success: bool, session_id: Optional[str] = None, **kwargs) -> None:
    """Quick logging of fallback event."""
    fallback = FallbackEvent(
        timestamp=time.time(),
        session_id=session_id,
        original_model=original_model,
        fallback_model=fallback_model,
        fallback_reason=reason,
        fallback_trigger=kwargs.get('fallback_trigger', 'unknown'),
        latency_ms=kwargs.get('latency_ms'),
        success=success,
        error_details=kwargs.get('error_details')
    )
    
    get_explainable_logger().log_fallback_event(fallback)
