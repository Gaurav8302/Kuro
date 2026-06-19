"""Insight Manager — CRUD, merging, reinforcement, contradiction handling.

Follows MEMORY_REFLECTION.md Sections 4 (Update Algorithm) and 6 (Invalidation).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from memory_v2.reflection.config import DEFAULT_REFLECTION_CONFIG, ReflectionConfig
from memory_v2.reflection.insight_store import InsightStore
from memory_v2.reflection.insight_validator import InsightValidator
from memory_v2.reflection.types import (
    ContradictionRef,
    Insight,
    InsightStatus,
    InsightType,
    SupportingMemoryRef,
)

logger = logging.getLogger(__name__)


class InsightManager:
    def __init__(
        self,
        store: Optional[InsightStore] = None,
        validator: Optional[InsightValidator] = None,
        config: Optional[ReflectionConfig] = None,
    ):
        self.config = config or DEFAULT_REFLECTION_CONFIG
        self.store = store or InsightStore(config=self.config)
        self.validator = validator or InsightValidator(config=self.config)

    # ── CRUD ──

    def insert_insight(self, user_id: str, insight: Insight) -> None:
        """Store a new insight."""
        now = _now_str()
        insight.created_at = now
        insight.updated_at = now
        insight.last_verified = now
        if insight.confidence >= self.config.min_confidence_for_active:
            insight.status = InsightStatus.ACTIVE
        else:
            insight.status = InsightStatus.PENDING
        self.store.upsert_insight(user_id, insight)
        logger.info(
            "New insight stored: '%s' (conf=%.2f, status=%s, evidence=%d)",
            insight.insight_text[:60],
            insight.confidence,
            insight.status.value,
            insight.evidence_count,
        )

    def update_insight(self, user_id: str, insight: Insight) -> None:
        """Update an existing insight's metadata and content."""
        insight.updated_at = _now_str()
        insight.version += 1
        self.store.upsert_insight(user_id, insight)

    def archive_insight(self, user_id: str, insight_id: str) -> bool:
        """Archive an insight."""
        insight = self.store.get_insight_by_id(user_id, insight_id)
        if not insight:
            return False
        insight.status = InsightStatus.ARCHIVED
        insight.updated_at = _now_str()
        self.store.upsert_insight(user_id, insight)
        logger.info("Insight archived: %s", insight_id)
        return True

    def archive_all_for_user(self, user_id: str, category: str = "") -> int:
        """Archive all active insights, optionally filtered by source category."""
        insights = self.store.get_active_insights(user_id)
        archived = 0
        for insight in insights:
            if category and category not in insight.source_categories:
                continue
            insight.status = InsightStatus.ARCHIVED
            insight.updated_at = _now_str()
            self.store.upsert_insight(user_id, insight)
            archived += 1
        return archived

    # ── Merge ──

    def merge_or_skip_duplicate(
        self, user_id: str, candidate: Insight, existing_insights: List[Insight]
    ) -> Tuple[bool, Optional[Insight]]:
        """Check if candidate is a duplicate of an existing insight.

        Returns (is_duplicate, merged_insight).
        If duplicate, the existing insight is updated in place.
        """
        for existing in existing_insights:
            if existing.status == "archived":
                continue

            jaccard = self._jaccard_between(candidate.insight_text, existing.insight_text)
            if jaccard > 0.85:
                merged = self._merge_insights(existing, candidate)
                self.store.upsert_insight(user_id, merged)
                logger.info(
                    "Merged duplicate insight (jaccard=%.2f): %s -> %s",
                    jaccard, existing.id, candidate.insight_text[:40],
                )
                return True, merged

        return False, None

    def _merge_insights(self, primary: Insight, secondary: Insight) -> Insight:
        """Merge secondary insight into primary (primary takes precedence for id and creation)."""
        now = _now_str()

        if len(secondary.insight_text) > len(primary.insight_text) * 1.3:
            primary.insight_text = secondary.insight_text

        existing_ids = {m.id for m in primary.supporting_memories}
        for mem in secondary.supporting_memories:
            if mem.id not in existing_ids:
                primary.supporting_memories.append(mem)
                existing_ids.add(mem.id)

        primary.confidence = max(primary.confidence, secondary.confidence)
        primary.importance = min(10.0, (
            (primary.get("importance", 5.0) if isinstance(primary, dict) else 5.0) + 0.5
        ))
        primary.evidence_count = len(primary.supporting_memories)

        existing_categories = set(primary.source_categories)
        for cat in secondary.source_categories:
            if cat not in existing_categories:
                primary.source_categories.append(cat)
                existing_categories.add(cat)

        primary.version += 1
        primary.updated_at = now
        primary.last_verified = now

        return primary

    # ── Contradiction handling ──

    def handle_contradictions(
        self,
        user_id: str,
        candidate: Insight,
        conflicting: List[Tuple[Insight, float]],
    ) -> None:
        """Handle contradictions between candidate and existing insights.

        Follows MEMORY_REFLECTION.md Section 3 (Step 5 — Contradiction Check).
        """
        for existing, strength in conflicting:
            candidate_score = candidate.confidence * candidate.evidence_count
            existing_score = existing.confidence * existing.evidence_count

            if existing_score >= candidate_score:
                existing.status = InsightStatus.CONTESTED
                existing.contradictions.append(ContradictionRef(
                    id=candidate.id,
                    content=candidate.insight_text,
                    strength=strength,
                ))
                existing.updated_at = _now_str()
                self.store.upsert_insight(user_id, existing)
                candidate.status = InsightStatus.CONTESTED
                logger.info(
                    "Contradiction: existing '%s' (%.2f) beats candidate '%s' (%.2f)",
                    existing.summary_label or existing.insight_text[:30],
                    existing_score,
                    candidate.insight_text[:30],
                    candidate_score,
                )
            else:
                candidate.contradictions.append(ContradictionRef(
                    id=existing.id,
                    content=existing.insight_text,
                    strength=strength,
                ))
                existing.status = InsightStatus.CONTESTED
                existing.updated_at = _now_str()
                self.store.upsert_insight(user_id, existing)
                logger.info(
                    "Contradiction: candidate '%s' (%.2f) beats existing '%s' (%.2f)",
                    candidate.insight_text[:30],
                    candidate_score,
                    existing.summary_label or existing.insight_text[:30],
                    existing_score,
                )

    # ── Reinforcement and decay ──

    def reinforce(self, user_id: str, insight_id: str) -> None:
        """Reinforce an insight — increment activation count, boost confidence."""
        insight = self.store.get_insight_by_id(user_id, insight_id)
        if not insight:
            return
        now = _now_str()
        insight.activation_count = (insight.activation_count or 0) + 1
        insight.last_activated = now
        insight.last_verified = now
        insight.confidence = min(1.0, insight.confidence + 0.02)
        self.store.upsert_insight(user_id, insight)

    def decay(self, user_id: str) -> int:
        """Apply confidence decay to all insights.

        Returns number of insights archived due to decay.
        """
        store_data = self.store.load_all(user_id)
        now = datetime.now(timezone.utc)
        archived = 0

        for insight in store_data.insights:
            if insight.status == "archived":
                continue

            last_update = _parse_time(insight.last_verified or insight.updated_at)
            days_since = max(0, (now - last_update).days)

            if days_since > self.config.decay_days_no_reinforcement:
                decay_factor = self.config.decay_factor_per_day ** days_since
                insight.confidence *= decay_factor

                if insight.confidence < self.config.archive_confidence_threshold:
                    insight.status = InsightStatus.ARCHIVED
                    logger.info(
                        "Insight archived by decay: '%s' (conf fell to %.2f)",
                        insight.insight_text[:40],
                        insight.confidence,
                    )
                    archived += 1

                insight.updated_at = _now_str()

        self.store.save_all(store_data)
        return archived

    # ── Correction handling ──

    def handle_correction(
        self, user_id: str, message: str
    ) -> List[str]:
        """Handle user correction signal — archive relevant insights.

        Returns list of archived insight IDs.
        """
        if not self.validator.check_correction_signal(message):
            return []

        insights = self.store.get_active_insights(user_id)
        msg_lower = message.lower()
        archived_ids = []

        for insight in insights:
            text_lower = insight.insight_text.lower()
            msg_words = set(msg_lower.split())
            insight_words = set(text_lower.split())
            word_overlap = len(msg_words & insight_words) / max(len(insight_words), 1)

            if word_overlap > 0.15:
                insight.confidence *= self.config.correction_confidence_multiplier
                if insight.confidence < self.config.archive_confidence_threshold:
                    insight.status = InsightStatus.ARCHIVED
                    archived_ids.append(insight.id)
                insight.updated_at = _now_str()
                self.store.upsert_insight(user_id, insight)
                logger.info(
                    "Correction signal applied to insight %s (conf now %.2f)",
                    insight.id, insight.confidence,
                )

        return archived_ids

    # ── Scoring recomputation ──

    def recompute_confidence(
        self,
        insight: Insight,
        cluster: List[dict],
        existing_insights: List[Insight],
    ) -> float:
        """Recompute insight confidence using formula from MEMORY_REFLECTION.md.

        confidence = (coherence × coverage × specificity × stability)^(1/4)
        """
        coherence = self._compute_coherence(cluster)
        coverage = self._compute_coverage(cluster)
        specificity = self.validator.compute_specificity(
            insight.insight_text, existing_insights
        )
        stability = self.validator.compute_stability(cluster)

        raw = coherence * coverage * specificity * stability
        confidence = raw ** 0.25
        return round(max(0.0, min(1.0, confidence)), 4)

    def _compute_coherence(self, cluster: List[dict]) -> float:
        """Average pairwise cosine similarity within cluster."""
        if len(cluster) < 2:
            return 0.5
        embeddings = []
        for mem in cluster:
            emb = mem.get("embedding")
            if emb:
                embeddings.append(emb)
        if len(embeddings) < 2:
            return 0.6

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
        if not similarities:
            return 0.6
        return sum(similarities) / len(similarities)

    def _compute_coverage(self, cluster: List[dict]) -> float:
        """How much of the memory landscape this insight covers."""
        types_seen = set()
        for mem in cluster:
            mt = mem.get("type") or mem.get("metadata", {}).get("type", "unknown")
            types_seen.add(mt)
        type_diversity = len(types_seen) / 4.0

        timestamps = []
        for mem in cluster:
            ts = mem.get("timestamp") or mem.get("created_at", "")
            if ts:
                try:
                    timestamps.append(
                        datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    )
                except (ValueError, TypeError):
                    continue
        temporal_spread = 0.0
        if len(timestamps) >= 2:
            span_days = max(1, (max(timestamps) - min(timestamps)).days)
            temporal_spread = min(1.0, span_days / 90.0)

        return min(1.0, type_diversity * max(temporal_spread, 0.1))

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _jaccard_between(self, text_a: str, text_b: str) -> float:
        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)
