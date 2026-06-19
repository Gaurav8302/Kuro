"""Data classes for the Reflection Engine insight system."""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class InsightType(str, Enum):
    TRAIT = "trait"
    PATTERN = "pattern"
    CONTRADICTION = "contradiction"
    SUMMARY = "summary"


class InsightStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    CONTESTED = "contested"
    ARCHIVED = "archived"


@dataclass
class SupportingMemoryRef:
    id: str
    type: str
    content: str
    relevance: float  # 0.0–1.0 how relevant to the insight

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "relevance": self.relevance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SupportingMemoryRef:
        return cls(
            id=data["id"],
            type=data["type"],
            content=data["content"],
            relevance=float(data.get("relevance", 0.0)),
        )


@dataclass
class ContradictionRef:
    id: str
    content: str
    strength: float  # 0.0–1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "strength": self.strength,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContradictionRef:
        return cls(
            id=data["id"],
            content=data["content"],
            strength=float(data.get("strength", 0.0)),
        )


@dataclass
class Insight:
    id: str
    insight_text: str
    insight_type: InsightType
    confidence: float
    supporting_memories: List[SupportingMemoryRef] = field(default_factory=list)
    source_categories: List[str] = field(default_factory=list)
    evidence_count: int = 0
    memory_diversity: float = 0.0
    temporal_span_days: int = 0
    status: InsightStatus = InsightStatus.PENDING
    version: int = 1
    activation_count: int = 0
    contradictions: List[ContradictionRef] = field(default_factory=list)
    summary_label: str = ""
    reasoning: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_verified: str = ""
    last_activated: str = ""

    @property
    def is_active(self) -> bool:
        return self.status == InsightStatus.ACTIVE

    @property
    def is_pending(self) -> bool:
        return self.status == InsightStatus.PENDING

    @property
    def is_contested(self) -> bool:
        return self.status == InsightStatus.CONTESTED

    @property
    def is_archived(self) -> bool:
        return self.status == InsightStatus.ARCHIVED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "insight_text": self.insight_text,
            "insight_type": self.insight_type.value,
            "confidence": self.confidence,
            "supporting_memories": [m.to_dict() for m in self.supporting_memories],
            "source_categories": self.source_categories,
            "evidence_count": self.evidence_count,
            "memory_diversity": self.memory_diversity,
            "temporal_span_days": self.temporal_span_days,
            "status": self.status.value,
            "version": self.version,
            "activation_count": self.activation_count,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "summary_label": self.summary_label,
            "reasoning": self.reasoning,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_verified": self.last_verified,
            "last_activated": self.last_activated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Insight:
        return cls(
            id=data["id"],
            insight_text=data["insight_text"],
            insight_type=InsightType(data.get("insight_type", "trait")),
            confidence=float(data.get("confidence", 0.0)),
            supporting_memories=[
                SupportingMemoryRef.from_dict(m)
                for m in data.get("supporting_memories", [])
            ],
            source_categories=data.get("source_categories", []),
            evidence_count=int(data.get("evidence_count", 0)),
            memory_diversity=float(data.get("memory_diversity", 0.0)),
            temporal_span_days=int(data.get("temporal_span_days", 0)),
            status=InsightStatus(data.get("status", "pending")),
            version=int(data.get("version", 1)),
            activation_count=int(data.get("activation_count", 0)),
            contradictions=[
                ContradictionRef.from_dict(c)
                for c in data.get("contradictions", [])
            ],
            summary_label=data.get("summary_label", ""),
            reasoning=data.get("reasoning", ""),
            created_at=data.get("created_at", _now_str()),
            updated_at=data.get("updated_at", _now_str()),
            last_verified=data.get("last_verified", ""),
            last_activated=data.get("last_activated", ""),
        )

    @classmethod
    def create(
        cls,
        insight_text: str,
        insight_type: InsightType,
        supporting_memories: List[SupportingMemoryRef],
        source_categories: List[str],
        reasoning: str = "",
        summary_label: str = "",
    ) -> Insight:
        now = _now_str()
        evidence = len(supporting_memories)
        return cls(
            id=_generate_id(),
            insight_text=insight_text,
            insight_type=insight_type,
            confidence=0.0,
            supporting_memories=supporting_memories,
            source_categories=source_categories,
            evidence_count=evidence,
            status=InsightStatus.PENDING,
            reasoning=reasoning,
            summary_label=summary_label,
            created_at=now,
            updated_at=now,
            last_verified=now,
        )


@dataclass
class InsightStoreData:
    version: int = 1
    user_id: str = ""
    insights: List[Insight] = field(default_factory=list)
    global_config: dict = field(default_factory=lambda: {
        "min_evidence_for_insight": 3,
        "min_confidence_for_active": 0.65,
        "max_insights_per_user": 20,
        "decay_days_no_reinforcement": 60,
    })

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "user_id": self.user_id,
            "insights": [i.to_dict() for i in self.insights],
            "global": dict(self.global_config),
        }

    @classmethod
    def from_dict(cls, data: dict) -> InsightStoreData:
        return cls(
            version=int(data.get("version", 1)),
            user_id=data.get("user_id", ""),
            insights=[Insight.from_dict(i) for i in data.get("insights", [])],
            global_config=data.get("global", {}),
        )


def _generate_id() -> str:
    return f"ins_{uuid.uuid4().hex[:12]}"


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
