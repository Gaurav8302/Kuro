"""Reflection Engine configuration — tunable constants."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ReflectionConfig:
    # ── Pipeline thresholds ──
    min_cluster_size: int = 3
    min_confidence_for_storage: float = 0.50
    min_confidence_for_active: float = 0.65
    max_insights_per_user: int = 20
    cluster_similarity_threshold: float = 0.65
    duplicate_cosine_threshold: float = 0.85
    related_cosine_threshold: float = 0.65

    # ── Evidence requirements ──
    min_memories_for_reflection: int = 3
    min_temporal_span_days: int = 7
    memory_lookback_days: int = 90
    min_memory_confidence: float = 0.50

    # ── Decay ──
    decay_days_no_reinforcement: int = 60
    decay_factor_per_day: float = 0.97
    archive_confidence_threshold: float = 0.30
    correction_confidence_multiplier: float = 0.3

    # ── Scheduling ──
    reflection_after_n_memories: int = 10
    reflection_interval_minutes: int = 1440  # 24 hours
    reflection_on_session_end: bool = True

    # ── Scoring weights (geometric mean) ──
    coherence_weight: float = 1.0
    coverage_weight: float = 1.0
    specificity_weight: float = 1.0
    stability_weight: float = 1.0

    # ── Retrieval ──
    max_insights_for_injection: int = 5
    insight_injection_confidence_floor: float = 0.65
    insight_relevance_threshold: float = 0.50

    # ── Storage ──
    storage_path: str = "backend/memory_v2/data"
    insights_filename: str = "insights.json"

    # ── Hallucination guardrails ──
    min_insight_words: int = 8
    max_insight_words: int = 35
    specificity_length_low: int = 8
    specificity_length_high: int = 16


DEFAULT_REFLECTION_CONFIG = ReflectionConfig()
