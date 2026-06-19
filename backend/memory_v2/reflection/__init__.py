"""Reflection Engine package — higher-level insight generation from stored memories."""

from memory_v2.reflection.engine import ReflectionEngine
from memory_v2.reflection.insight_manager import InsightManager
from memory_v2.reflection.insight_store import InsightStore
from memory_v2.reflection.insight_validator import InsightValidator
from memory_v2.reflection.scheduler import ReflectionScheduler
from memory_v2.reflection.config import ReflectionConfig, DEFAULT_REFLECTION_CONFIG
from memory_v2.reflection.types import (
    Insight,
    InsightType,
    InsightStatus,
    SupportingMemoryRef,
    ContradictionRef,
    InsightStoreData,
)

__all__ = [
    "ReflectionEngine",
    "InsightManager",
    "InsightStore",
    "InsightValidator",
    "ReflectionScheduler",
    "ReflectionConfig",
    "DEFAULT_REFLECTION_CONFIG",
    "Insight",
    "InsightType",
    "InsightStatus",
    "SupportingMemoryRef",
    "ContradictionRef",
    "InsightStoreData",
]
