"""Circuit breaker and failure tracking for resilient model routing.

Implements the circuit breaker pattern to automatically handle model failures
and provide intelligent fallback routing with failure memory.
"""
from __future__ import annotations
import time
import logging
from typing import Dict, Optional, List, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
import threading
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Circuit breaker tripped, rejecting requests  
    HALF_OPEN = "half_open" # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Failures needed to trip
    success_threshold: int = 2          # Successes needed to close from half-open
    timeout_seconds: int = 60           # Time before trying half-open
    rolling_window_seconds: int = 300   # Window for counting failures
    max_failure_rate: float = 0.5       # Maximum failure rate to allow (0.0-1.0)


@dataclass
class ModelFailureData:
    """Tracks failure data for a specific model."""
    model_id: str
    total_requests: int = 0
    total_failures: int = 0
    recent_failures: List[float] = field(default_factory=list)  # Timestamps
    recent_successes: List[float] = field(default_factory=list)  # Timestamps
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    circuit_state: CircuitState = CircuitState.CLOSED
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    circuit_opened_at: float = 0.0
    
    def cleanup_old_entries(self, window_seconds: int):
        """Remove entries older than the rolling window."""
        cutoff = time.time() - window_seconds
        self.recent_failures = [t for t in self.recent_failures if t > cutoff]
        self.recent_successes = [t for t in self.recent_successes if t > cutoff]


class CircuitBreaker:
    """Circuit breaker for model failure handling."""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._model_data: Dict[str, ModelFailureData] = {}
        self._lock = threading.Lock()
        
        # Persistence for failure data
        self.persistence_file = Path(__file__).parent.parent / "data" / "circuit_breaker.json"
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_failure_data()
    
    def _load_failure_data(self):
        """Load persisted failure data."""
        if not self.persistence_file.exists():
            return
            
        try:
            with self.persistence_file.open('r') as f:
                data = json.load(f)
            
            for model_id, model_data in data.get('models', {}).items():
                failure_data = ModelFailureData(
                    model_id=model_id,
                    total_requests=model_data.get('total_requests', 0),
                    total_failures=model_data.get('total_failures', 0),
                    recent_failures=model_data.get('recent_failures', []),
                    recent_successes=model_data.get('recent_successes', []),
                    consecutive_failures=model_data.get('consecutive_failures', 0),
                    consecutive_successes=model_data.get('consecutive_successes', 0),
                    circuit_state=CircuitState(model_data.get('circuit_state', 'closed')),
                    last_failure_time=model_data.get('last_failure_time', 0.0),
                    last_success_time=model_data.get('last_success_time', 0.0),
                    circuit_opened_at=model_data.get('circuit_opened_at', 0.0)
                )
                
                # Clean up old entries
                failure_data.cleanup_old_entries(self.config.rolling_window_seconds)
                self._model_data[model_id] = failure_data
            
            logger.info(f"Loaded circuit breaker data for {len(self._model_data)} models")
            
        except Exception as e:
            logger.warning(f"Failed to load circuit breaker data: {str(e)}")
    
    def _save_failure_data(self):
        """Persist failure data."""
        try:
            data = {
                'models': {},
                'last_updated': time.time()
            }
            
            for model_id, failure_data in self._model_data.items():
                data['models'][model_id] = {
                    'total_requests': failure_data.total_requests,
                    'total_failures': failure_data.total_failures,
                    'recent_failures': failure_data.recent_failures,
                    'recent_successes': failure_data.recent_successes,
                    'consecutive_failures': failure_data.consecutive_failures,
                    'consecutive_successes': failure_data.consecutive_successes,
                    'circuit_state': failure_data.circuit_state.value,
                    'last_failure_time': failure_data.last_failure_time,
                    'last_success_time': failure_data.last_success_time,
                    'circuit_opened_at': failure_data.circuit_opened_at
                }
            
            with self.persistence_file.open('w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save circuit breaker data: {str(e)}")
    
    def _get_model_data(self, model_id: str) -> ModelFailureData:
        """Get or create failure data for a model."""
        if model_id not in self._model_data:
            self._model_data[model_id] = ModelFailureData(model_id=model_id)
        return self._model_data[model_id]
    
    def _update_circuit_state(self, model_data: ModelFailureData):
        """Update circuit breaker state based on recent activity."""
        now = time.time()
        
        # Clean up old entries
        model_data.cleanup_old_entries(self.config.rolling_window_seconds)
        
        current_state = model_data.circuit_state
        
        if current_state == CircuitState.CLOSED:
            # Check if we should trip the circuit
            recent_failure_count = len(model_data.recent_failures)
            
            # Trip if too many consecutive failures
            if model_data.consecutive_failures >= self.config.failure_threshold:
                model_data.circuit_state = CircuitState.OPEN
                model_data.circuit_opened_at = now
                logger.warning(f"Circuit breaker OPENED for {model_data.model_id} - {model_data.consecutive_failures} consecutive failures")
            
            # Trip if failure rate is too high
            elif recent_failure_count >= self.config.failure_threshold:
                total_recent = len(model_data.recent_failures) + len(model_data.recent_successes)
                if total_recent > 0:
                    failure_rate = recent_failure_count / total_recent
                    if failure_rate >= self.config.max_failure_rate:
                        model_data.circuit_state = CircuitState.OPEN
                        model_data.circuit_opened_at = now
                        logger.warning(f"Circuit breaker OPENED for {model_data.model_id} - failure rate {failure_rate:.2f}")
        
        elif current_state == CircuitState.OPEN:
            # Check if we should try half-open
            time_since_opened = now - model_data.circuit_opened_at
            if time_since_opened >= self.config.timeout_seconds:
                model_data.circuit_state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker HALF-OPEN for {model_data.model_id} - testing recovery")
        
        elif current_state == CircuitState.HALF_OPEN:
            # Check if we should close or reopen
            if model_data.consecutive_successes >= self.config.success_threshold:
                model_data.circuit_state = CircuitState.CLOSED
                logger.info(f"Circuit breaker CLOSED for {model_data.model_id} - service recovered")
            elif model_data.consecutive_failures >= 1:
                model_data.circuit_state = CircuitState.OPEN
                model_data.circuit_opened_at = now
                logger.warning(f"Circuit breaker RE-OPENED for {model_data.model_id} - still failing")
    
    def can_execute(self, model_id: str) -> Tuple[bool, str]:
        """Check if a request can be executed for this model."""
        with self._lock:
            model_data = self._get_model_data(model_id)
            self._update_circuit_state(model_data)
            
            if model_data.circuit_state == CircuitState.OPEN:
                return False, f"circuit_breaker_open:failures={model_data.consecutive_failures}"
            elif model_data.circuit_state == CircuitState.HALF_OPEN:
                return True, "circuit_breaker_testing"
            else:
                return True, "circuit_breaker_closed"
    
    def record_success(self, model_id: str):
        """Record a successful request."""
        now = time.time()
        
        with self._lock:
            model_data = self._get_model_data(model_id)
            
            model_data.total_requests += 1
            model_data.recent_successes.append(now)
            model_data.consecutive_successes += 1
            model_data.consecutive_failures = 0
            model_data.last_success_time = now
            
            self._update_circuit_state(model_data)
            
            # Periodic save (every 10 requests to avoid excessive I/O)
            if model_data.total_requests % 10 == 0:
                self._save_failure_data()
    
    def record_failure(self, model_id: str, error_type: str = "unknown"):
        """Record a failed request."""
        now = time.time()
        
        with self._lock:
            model_data = self._get_model_data(model_id)
            
            model_data.total_requests += 1
            model_data.total_failures += 1
            model_data.recent_failures.append(now)
            model_data.consecutive_failures += 1
            model_data.consecutive_successes = 0
            model_data.last_failure_time = now
            
            self._update_circuit_state(model_data)
            
            logger.warning(f"Model failure recorded: {model_id} - {error_type} (consecutive: {model_data.consecutive_failures})")
            
            # Save immediately on failures for reliability
            self._save_failure_data()
    
    def get_model_health(self, model_id: str) -> Dict[str, any]:
        """Get health information for a model."""
        with self._lock:
            model_data = self._get_model_data(model_id)
            self._update_circuit_state(model_data)
            
            # Calculate recent metrics
            now = time.time()
            cutoff = now - self.config.rolling_window_seconds
            recent_failures = len([t for t in model_data.recent_failures if t > cutoff])
            recent_successes = len([t for t in model_data.recent_successes if t > cutoff])
            total_recent = recent_failures + recent_successes
            
            failure_rate = recent_failures / max(1, total_recent)
            
            return {
                'model_id': model_id,
                'circuit_state': model_data.circuit_state.value,
                'can_execute': model_data.circuit_state != CircuitState.OPEN,
                'total_requests': model_data.total_requests,
                'total_failures': model_data.total_failures,
                'consecutive_failures': model_data.consecutive_failures,
                'consecutive_successes': model_data.consecutive_successes,
                'recent_failure_rate': failure_rate,
                'recent_failures': recent_failures,
                'recent_successes': recent_successes,
                'last_failure': model_data.last_failure_time,
                'last_success': model_data.last_success_time,
                'overall_failure_rate': model_data.total_failures / max(1, model_data.total_requests)
            }
    
    def get_healthy_models(self, model_ids: List[str]) -> List[str]:
        """Filter list of models to only include healthy ones."""
        healthy = []
        
        for model_id in model_ids:
            can_execute, _ = self.can_execute(model_id)
            if can_execute:
                healthy.append(model_id)
        
        return healthy
    
    def get_ranked_models(self, model_ids: List[str]) -> List[Tuple[str, float]]:
        """Rank models by health score (higher = healthier)."""
        ranked = []
        
        for model_id in model_ids:
            health = self.get_model_health(model_id)
            
            # Calculate health score (0.0 to 1.0)
            if health['circuit_state'] == 'open':
                score = 0.0
            elif health['circuit_state'] == 'half_open':
                score = 0.3
            else:
                # Base score on recent failure rate
                failure_rate = health['recent_failure_rate']
                score = max(0.1, 1.0 - failure_rate)
                
                # Bonus for consistent recent successes
                if health['consecutive_successes'] > 0:
                    score += min(0.2, health['consecutive_successes'] * 0.05)
            
            ranked.append((model_id, score))
        
        # Sort by health score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    def reset_model(self, model_id: str):
        """Reset circuit breaker data for a model (useful for testing/recovery)."""
        with self._lock:
            if model_id in self._model_data:
                del self._model_data[model_id]
                logger.info(f"Reset circuit breaker data for {model_id}")
                self._save_failure_data()
    
    def get_stats(self) -> Dict[str, any]:
        """Get overall circuit breaker statistics."""
        with self._lock:
            total_models = len(self._model_data)
            open_circuits = sum(1 for data in self._model_data.values() 
                              if data.circuit_state == CircuitState.OPEN)
            half_open_circuits = sum(1 for data in self._model_data.values() 
                                   if data.circuit_state == CircuitState.HALF_OPEN)
            
            return {
                'total_models_tracked': total_models,
                'open_circuits': open_circuits,
                'half_open_circuits': half_open_circuits,
                'healthy_circuits': total_models - open_circuits - half_open_circuits,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'timeout_seconds': self.config.timeout_seconds,
                    'max_failure_rate': self.config.max_failure_rate
                }
            }


# Global singleton instance
_circuit_breaker = None
_init_lock = threading.Lock()

def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance (singleton)."""
    global _circuit_breaker
    
    if _circuit_breaker is None:
        with _init_lock:
            if _circuit_breaker is None:
                _circuit_breaker = CircuitBreaker()
    
    return _circuit_breaker
