"""Memory v2 — Production-grade multi-layer memory system for Kuro.

Layers:
  - Working Memory (in-memory, current session)
  - Episodic Memory (JSON-persisted, events)
  - Semantic Memory (JSON-persisted, facts)
  - Preference Memory (JSON-persisted, preferences)
  - Procedural Memory (JSON-persisted, behavior patterns)
  - Reflection Engine (meta-layer, insights across stores)

This package exports the ReflectionEngine as the main entry point
for the meta-cognitive insight layer.
"""

from memory_v2.reflection.engine import ReflectionEngine
from memory_v2.reflection.config import ReflectionConfig, DEFAULT_REFLECTION_CONFIG
from memory_v2.reflection.types import Insight, InsightType, InsightStatus
from memory_v2.integration import ReflectionIntegration

__all__ = [
    "ReflectionEngine",
    "ReflectionConfig",
    "DEFAULT_REFLECTION_CONFIG",
    "ReflectionIntegration",
    "Insight",
    "InsightType",
    "InsightStatus",
]
