"""Insight validation — hallucination prevention and quality gates.

Follows the validation rules from MEMORY_REFLECTION.md Section 3 (Step 5).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from memory_v2.reflection.config import DEFAULT_REFLECTION_CONFIG, ReflectionConfig
from memory_v2.reflection.types import (
    ContradictionRef,
    Insight,
    InsightStatus,
    InsightType,
    SupportingMemoryRef,
)

logger = logging.getLogger(__name__)


class InsightValidator:
    def __init__(self, config: Optional[ReflectionConfig] = None):
        self.config = config or DEFAULT_REFLECTION_CONFIG

    def validate(
        self, candidate: Insight, existing_insights: List[Insight], cluster: List[dict]
    ) -> Tuple[bool, str]:
        """Run all validation checks. Returns (is_valid, rejection_reason)."""
        checks = [
            ("min_evidence", self._check_min_evidence(candidate)),
            ("min_temporal_span", self._check_temporal_span(cluster)),
            ("not_single_session", self._check_not_single_session(cluster)),
            ("not_verbatim_copy", self._check_not_verbatim_copy(candidate, cluster)),
            ("not_vague", self._check_not_vague(candidate)),
            ("not_over_extrapolation", self._check_over_extrapolation(candidate, cluster)),
            ("supported_by_cluster", self._check_supported_by_cluster(candidate, cluster)),
        ]
        for check_name, result in checks:
            if result is not None:
                return False, f"{check_name}: {result}"
        return True, ""

    def _check_min_evidence(self, candidate: Insight) -> Optional[str]:
        if candidate.evidence_count < self.config.min_cluster_size:
            return f"evidence_count {candidate.evidence_count} < min {self.config.min_cluster_size}"
        return None

    def _check_temporal_span(self, cluster: List[dict]) -> Optional[str]:
        timestamps = [
            m.get("timestamp") or m.get("created_at", "")
            for m in cluster
            if m.get("timestamp") or m.get("created_at")
        ]
        if len(timestamps) < 2:
            return None
        try:
            parsed = [
                datetime.fromisoformat(t.replace("Z", "+00:00"))
                for t in timestamps
            ]
            span_days = max(0, (max(parsed) - min(parsed)).days)
            if span_days < self.config.min_temporal_span_days:
                return (
                    f"temporal span {span_days}d < min {self.config.min_temporal_span_days}d"
                )
        except (ValueError, TypeError):
            pass
        return None

    def _check_not_single_session(self, cluster: List[dict]) -> Optional[str]:
        session_ids: Set[str] = set()
        for m in cluster:
            sid = m.get("session_id") or m.get("metadata", {}).get("session_id", "")
            if sid:
                session_ids.add(str(sid))
        if len(session_ids) <= 1 and len(cluster) >= self.config.min_cluster_size:
            return "all memories from single session"
        return None

    def _check_not_verbatim_copy(self, candidate: Insight, cluster: List[dict]) -> Optional[str]:
        candidate_lower = candidate.insight_text.lower().strip()
        for mem in cluster:
            content = (mem.get("content") or "").lower().strip()
            if not content:
                continue
            jaccard = self._jaccard_similarity(
                set(candidate_lower.split()),
                set(content.split()),
            )
            if jaccard > 0.85:
                return f"insight is near-verbatim copy of a memory (jaccard={jaccard:.2f})"
        return None

    def _check_not_vague(self, candidate: Insight) -> Optional[str]:
        words = candidate.insight_text.strip().split()
        if len(words) < self.config.min_insight_words:
            return f"insight too short ({len(words)} words < min {self.config.min_insight_words})"
        if len(words) > self.config.max_insight_words:
            return f"insight too verbose ({len(words)} words > max {self.config.max_insight_words})"
        hedging = {"maybe", "perhaps", "kind of", "sort of", "i think", "i feel", "might be", "could be"}
        text_lower = candidate.insight_text.lower()
        if any(h in text_lower for h in hedging):
            return "insight contains hedging language"
        return None

    def _check_over_extrapolation(self, candidate: Insight, cluster: List[dict]) -> Optional[str]:
        """Check that the insight doesn't claim things unsupported by evidence."""
        insight_lower = candidate.insight_text.lower()
        cluster_texts = [(m.get("content") or "").lower() for m in cluster]
        combined = " ".join(cluster_texts)

        identity_claims = re.findall(
            r"\b(user is|user works as|user is a|user's job|user's profession)\b",
            insight_lower,
        )
        if identity_claims:
            has_backing = any(
                re.search(r"\b(work as|job|profession|engineer|developer|student|manager)\b", t)
                for t in cluster_texts
            )
            if not has_backing:
                return "identity claim not supported by cluster"

        return None

    def _check_supported_by_cluster(self, candidate: Insight, cluster: List[dict]) -> Optional[str]:
        """Check insight is actually supported by cluster contents."""
        insight_lower = candidate.insight_text.lower()
        insight_words = set(w for w in insight_lower.split() if len(w) > 3)
        if not insight_words:
            return None
        cluster_words: Set[str] = set()
        for m in cluster:
            cluster_words.update(
                w for w in (m.get("content") or "").lower().split() if len(w) > 3
            )
        overlap = len(insight_words & cluster_words)
        ratio = overlap / max(len(insight_words), 1)
        if ratio < 0.15:
            return f"insight shares only {ratio:.2f} word overlap with cluster"
        return None

    def detect_contradictions(
        self, candidate: Insight, existing_insights: List[Insight]
    ) -> List[Tuple[Insight, float]]:
        """Find existing insights that contradict the candidate.

        Returns list of (conflicting_insight, conflict_strength).
        """
        conflicts: List[Tuple[Insight, float]] = []
        for existing in existing_insights:
            if existing.status == "archived":
                continue
            strength = self._estimate_contradiction_strength(candidate, existing)
            if strength > 0.4:
                conflicts.append((existing, strength))
        return conflicts

    def _estimate_contradiction_strength(self, a: Insight, b: Insight) -> float:
        """Estimate how strongly two insights contradict each other."""
        text_a = a.insight_text.lower()
        text_b = b.insight_text.lower()

        negation_pairs = [
            ({"like", "love", "prefer"}, {"dislike", "hate", "avoid"}),
            ({"local", "self-host", "self-hosted"}, {"cloud", "saas", "hosted"}),
            ({"privacy", "private", "secure"}, {"convenience", "easy", "simple"}),
            ({"concise", "short", "brief"}, {"detailed", "in-depth", "thorough"}),
        ]

        max_strength = 0.0
        for pos_words, neg_words in negation_pairs:
            has_pos = any(w in text_a for w in pos_words) or any(w in text_b for w in pos_words)
            has_neg_a = any(w in text_a for w in neg_words)
            has_neg_b = any(w in text_b for w in neg_words)
            if has_pos and (has_neg_a or has_neg_b) and (text_a != text_b):
                strength = 0.6
                if a.source_categories and b.source_categories:
                    shared = set(a.source_categories) & set(b.source_categories)
                    if shared:
                        strength = 0.8
                    diverse = set(a.source_categories) ^ set(b.source_categories)
                    if diverse and not shared:
                        strength = 0.4
                max_strength = max(max_strength, strength)

        return max_strength

    def check_correction_signal(self, message: str) -> bool:
        """Detect if user is correcting Kuro's assumptions about them."""
        patterns = [
            "don't assume",
            "stop assuming",
            "that's not right",
            "that's wrong",
            "no, i",
            "actually, i don't",
            "why do you think",
            "i never said",
            "you keep",
            "stop doing",
        ]
        msg_lower = message.lower()
        return any(p in msg_lower for p in patterns)

    def compute_specificity(self, text: str, existing_insights: List[Insight]) -> float:
        words = len(text.strip().split())
        if words < self.config.specificity_length_low:
            length_score = 0.50
        elif words < self.config.specificity_length_high:
            length_score = 0.80
        elif words <= self.config.max_insight_words:
            length_score = 1.00
        else:
            length_score = 0.90

        uniqueness = 1.0
        text_embedding_key = set(text.lower().split())
        for existing in existing_insights:
            existing_key = set(existing.insight_text.lower().split())
            overlap = len(text_embedding_key & existing_key) / max(
                len(text_embedding_key | existing_key), 1
            )
            if overlap > 0.80:
                uniqueness = 0.50
                break

        return length_score * uniqueness

    def compute_stability(self, cluster: List[dict]) -> float:
        timestamps = []
        for m in cluster:
            ts = m.get("timestamp") or m.get("created_at", "")
            if ts:
                try:
                    timestamps.append(
                        datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    )
                except (ValueError, TypeError):
                    continue
        if len(timestamps) < 3:
            return 0.5

        timestamps.sort()
        total_days = max(1, (timestamps[-1] - timestamps[0]).days)
        weeks = max(1, total_days // 7)
        counts_per_week = [0] * weeks
        start = timestamps[0]
        for ts in timestamps:
            week_index = min(weeks - 1, int((ts - start).days / 7))
            counts_per_week[week_index] += 1

        mean = sum(counts_per_week) / weeks
        if mean == 0:
            return 0.5
        variance = sum((c - mean) ** 2 for c in counts_per_week) / weeks
        std_dev = variance ** 0.5
        cv = std_dev / mean
        stability = 1.0 - min(0.5, cv / 2.0)
        return max(0.1, min(1.0, stability))

    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / max(len(union), 1)
