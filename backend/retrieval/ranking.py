"""Ranking utilities for RAG pipeline.

Combines multiple signals into a single score:
 - Vector similarity
 - Keyword match score
 - Recency (timestamp proximity)
 - Source reliability (configurable)
 - User preference tag boosts
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from .base import RetrievedChunk


@dataclass
class RankingWeights:
    similarity: float = 0.5
    keyword: float = 0.2
    recency: float = 0.15
    reliability: float = 0.1
    preference: float = 0.05


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp string into a timezone-aware UTC datetime.

    Ensures downstream arithmetic never mixes naive and aware datetimes.
    Returns None on parse failure.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Normalize to UTC without changing absolute time
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:  # pragma: no cover - defensive
        return None


def rank_chunks(
    chunks: List[RetrievedChunk],
    weights: RankingWeights,
    source_reliability: Optional[Dict[str, float]] = None,
    user_pref_tags: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not chunks:
        return []
    # Normalization of similarity & keyword
    max_sim = max((c.similarity for c in chunks), default=1.0) or 1.0
    max_kw = max((c.keyword_score for c in chunks), default=1.0) or 1.0
    now = datetime.now(timezone.utc)

    ranked = []
    for c in chunks:
        sim_norm = (c.similarity / max_sim) if max_sim else 0.0
        kw_norm = (c.keyword_score / max_kw) if max_kw else 0.0
        # Recency: exponential decay over days (recent => closer to 1)
        ts = _parse_timestamp(c.metadata.get("timestamp"))
        if ts:
            age_days = (now - ts).total_seconds() / 86400
            recency_score = 1 / (1 + age_days)  # simple decay
        else:
            recency_score = 0.3  # Neutral default
        reliability = 0.5
        if source_reliability:
            reliability = source_reliability.get(c.source, reliability)
        preference_score = 0.0
        if user_pref_tags:
            tags = []
            if isinstance(c.metadata.get("tags"), list):
                tags.extend(c.metadata.get("tags", []))
            if c.metadata.get("category"):
                tags.append(c.metadata.get("category"))
            overlap = set(t.lower() for t in tags) & set(t.lower() for t in user_pref_tags)
            if overlap:
                preference_score = min(1.0, len(overlap) / len(user_pref_tags))
        final_score = (
            sim_norm * weights.similarity
            + kw_norm * weights.keyword
            + recency_score * weights.recency
            + reliability * weights.reliability
            + preference_score * weights.preference
        )
        ranked.append(
            {
                "id": c.id,
                "text": c.text,
                "metadata": c.metadata,
                "similarity": c.similarity,
                "keyword_score": c.keyword_score,
                "score": final_score,
                "source": c.source,
            }
        )
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


__all__ = ["RankingWeights", "rank_chunks"]
