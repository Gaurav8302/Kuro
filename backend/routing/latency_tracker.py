"""Model latency tracking with Exponential Moving Average (EMA) for intelligent routing.

Maintains rolling averages of response times for each model to inform routing decisions.
Persists latency data to avoid cold starts affecting routing quality.
"""
from __future__ import annotations
import time
import json
import logging
from typing import Dict, Optional
from pathlib import Path
import threading
import os

logger = logging.getLogger(__name__)

class LatencyTracker:
    """Tracks and maintains EMA of model response latencies."""
    
    def __init__(self, alpha: float = 0.3, persistence_file: str = "model_latencies.json"):
        """Initialize latency tracker.
        
        Args:
            alpha: EMA smoothing factor (0.0-1.0). Higher = more weight to recent observations.
            persistence_file: JSON file to store latency data across restarts.
        """
        self.alpha = alpha
        self.persistence_file = Path(__file__).parent.parent / "data" / persistence_file
        self._latencies: Dict[str, float] = {}
        self._request_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        
        # Create data directory if it doesn't exist
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load persisted data
        self._load_latencies()
    
    def _load_latencies(self):
        """Load persisted latency data from JSON file."""
        if not self.persistence_file.exists():
            logger.info("No persisted latency data found, starting fresh")
            return
        
        try:
            with self.persistence_file.open('r') as f:
                data = json.load(f)
            
            self._latencies = data.get('latencies', {})
            self._request_counts = data.get('request_counts', {})
            
            logger.info(f"Loaded latency data for {len(self._latencies)} models")
            
        except Exception as e:
            logger.warning(f"Failed to load latency data: {str(e)}")
            self._latencies = {}
            self._request_counts = {}
    
    def _save_latencies(self):
        """Persist latency data to JSON file."""
        try:
            data = {
                'latencies': self._latencies,
                'request_counts': self._request_counts,
                'last_updated': time.time()
            }
            
            with self.persistence_file.open('w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save latency data: {str(e)}")
    
    def record_latency(self, model_id: str, latency_ms: float):
        """Record a latency observation for a model using EMA.
        
        Args:
            model_id: Model identifier
            latency_ms: Response time in milliseconds
        """
        with self._lock:
            if model_id in self._latencies:
                # Update EMA: new_avg = α * new_value + (1-α) * old_avg
                old_avg = self._latencies[model_id]
                self._latencies[model_id] = self.alpha * latency_ms + (1 - self.alpha) * old_avg
            else:
                # First observation for this model
                self._latencies[model_id] = latency_ms
            
            # Increment request count
            self._request_counts[model_id] = self._request_counts.get(model_id, 0) + 1
            
            # Periodically save data (every 10 requests to avoid excessive I/O)
            total_requests = sum(self._request_counts.values())
            if total_requests % 10 == 0:
                self._save_latencies()
    
    def get_latency(self, model_id: str) -> Optional[float]:
        """Get current EMA latency for a model in milliseconds."""
        with self._lock:
            return self._latencies.get(model_id)
    
    def get_latency_score(self, model_id: str, baseline_ms: float = 2000.0) -> float:
        """Get latency score for routing decisions.
        
        Returns a score where faster models get higher scores.
        Score = max(0, baseline - latency) / baseline
        
        Args:
            model_id: Model identifier
            baseline_ms: Baseline latency for scoring (default: 2000ms)
        
        Returns:
            Float between 0.0-1.0 where 1.0 = instant, 0.0 = at baseline or slower
        """
        latency = self.get_latency(model_id)
        if latency is None:
            return 0.5  # Neutral score for unknown models
        
        score = max(0.0, baseline_ms - latency) / baseline_ms
        return min(1.0, score)  # Cap at 1.0
    
    def get_all_latencies(self) -> Dict[str, float]:
        """Get all current latency EMAs."""
        with self._lock:
            return self._latencies.copy()
    
    def get_fastest_models(self, model_ids: list[str], top_k: int = 3) -> list[tuple[str, float]]:
        """Get the fastest models from a list, ranked by latency.
        
        Args:
            model_ids: List of model IDs to rank
            top_k: Number of top models to return
            
        Returns:
            List of (model_id, latency_ms) tuples, fastest first
        """
        model_latencies = []
        
        with self._lock:
            for model_id in model_ids:
                latency = self._latencies.get(model_id)
                if latency is not None:
                    model_latencies.append((model_id, latency))
                else:
                    # Unknown latency - assign middle value for fair consideration
                    model_latencies.append((model_id, 1500.0))
        
        # Sort by latency (ascending = fastest first)
        model_latencies.sort(key=lambda x: x[1])
        return model_latencies[:top_k]
    
    def get_request_count(self, model_id: str) -> int:
        """Get number of requests recorded for a model."""
        with self._lock:
            return self._request_counts.get(model_id, 0)
    
    def reset_model_data(self, model_id: str):
        """Reset latency data for a specific model (useful for model updates)."""
        with self._lock:
            self._latencies.pop(model_id, None)
            self._request_counts.pop(model_id, None)
            self._save_latencies()
    
    def get_stats(self) -> Dict[str, any]:
        """Get statistics about tracked models."""
        with self._lock:
            if not self._latencies:
                return {"models": 0, "fastest": None, "slowest": None, "average": 0}
            
            latencies = list(self._latencies.values())
            fastest_model = min(self._latencies, key=self._latencies.get)
            slowest_model = max(self._latencies, key=self._latencies.get)
            
            return {
                "models": len(self._latencies),
                "fastest": (fastest_model, self._latencies[fastest_model]),
                "slowest": (slowest_model, self._latencies[slowest_model]),
                "average": sum(latencies) / len(latencies),
                "total_requests": sum(self._request_counts.values())
            }


# Global singleton instance
_latency_tracker = None
_init_lock = threading.Lock()

def get_latency_tracker() -> LatencyTracker:
    """Get global latency tracker instance (singleton)."""
    global _latency_tracker
    
    if _latency_tracker is None:
        with _init_lock:
            if _latency_tracker is None:
                alpha = float(os.getenv('LATENCY_EMA_ALPHA', '0.3'))
                _latency_tracker = LatencyTracker(alpha=alpha)
    
    return _latency_tracker


class LatencyTimer:
    """Context manager for timing model requests."""
    
    def __init__(self, model_id: str, tracker: Optional[LatencyTracker] = None):
        self.model_id = model_id
        self.tracker = tracker or get_latency_tracker()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            latency_ms = (time.time() - self.start_time) * 1000
            self.tracker.record_latency(self.model_id, latency_ms)
            
            # Log if request was unusually slow
            if latency_ms > 5000:  # 5 seconds
                logger.warning(f"Slow model response: {self.model_id} took {latency_ms:.0f}ms")


# Usage example:
# with LatencyTimer('gpt-4o-mini'):
#     response = make_llm_request(...)
