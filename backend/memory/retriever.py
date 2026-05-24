"""
Memory Retriever — Vector Search + Rule-Based Ranking

Retrieves memories from Pinecone and ranks them using a weighted
scoring formula. No LLM calls in the retrieval/ranking path.

Previous version used an LLM to rerank results (~500ms per call).
Now uses a deterministic formula combining:
  - Vector similarity score (from Pinecone)
  - Importance score (from extraction)
  - Recency decay (temporal relevance)
  - Keyword overlap (lexical relevance)
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

from db.pinecone import query_vectors

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Retrieves and ranks memories without any LLM calls."""

    # Minimum vector similarity to consider a result
    MIN_SIMILARITY = 0.2

    # Minimum importance to consider a result (filters noise)
    MIN_IMPORTANCE = 1

    def __init__(self):
        # No LLM needed anymore
        pass

    async def retrieve(
        self,
        user_id: str,
        query: str,
        memory_types: List[str],
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve raw memories from vector DB."""
        results = query_vectors(
            query=query,
            user_id=user_id,
            memory_types=memory_types,
            top_k=top_k,
        )
        memories = [
            {
                "text": r.get("text", ""),
                "score": float(r.get("score", 0.0) or 0.0),
                "metadata": r.get("metadata", {}) or {},
            }
            for r in results
        ]

        # Filter by minimum thresholds
        memories = [
            m for m in memories
            if m["score"] >= self.MIN_SIMILARITY
            and float(m["metadata"].get("importance", 0) or 0) >= self.MIN_IMPORTANCE
        ]

        return memories

    async def rerank(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Re-rank memories using weighted scoring formula — zero LLM calls.

        Scoring formula:
          score = similarity * 0.45
                + importance * 0.20
                + recency    * 0.20
                + keyword    * 0.15
        """
        if not memories:
            return []

        query_tokens = set(self._tokenize(query))

        scored = []
        for mem in memories:
            sim_score = self._normalize(mem["score"], 0.0, 1.0)
            imp_score = self._normalize(
                float(mem["metadata"].get("importance", 5) or 5), 0.0, 10.0
            )
            rec_score = self._recency_score(mem["metadata"].get("timestamp"))
            kw_score = self._keyword_overlap(query_tokens, mem.get("text", ""))

            # Type boost: preferences and facts slightly more valuable than events
            type_boost = {"preference": 0.05, "fact": 0.03, "event": 0.0}.get(
                mem["metadata"].get("type", ""), 0.0
            )

            final = (
                sim_score * 0.45
                + imp_score * 0.20
                + rec_score * 0.20
                + kw_score * 0.15
                + type_boost
            )
            scored.append((mem, final))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:top_k]]

    # ---- Scoring helpers ----

    @staticmethod
    def _normalize(value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range."""
        if max_val <= min_val:
            return 0.0
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    @staticmethod
    def _recency_score(timestamp_str: str = None) -> float:
        """Score based on how recent the memory is. Returns 0-1."""
        if not timestamp_str:
            return 0.3  # Unknown age gets a neutral score

        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = max(0, (now - ts).total_seconds() / 86400)
            # Exponential decay: half-life of 30 days
            return 0.5 ** (age_days / 30.0)
        except Exception:
            return 0.3

    @staticmethod
    def _keyword_overlap(query_tokens: set, text: str) -> float:
        """Simple keyword overlap score between query and memory text."""
        if not query_tokens or not text:
            return 0.0
        text_tokens = set(MemoryRetriever._tokenize(text))
        if not text_tokens:
            return 0.0
        overlap = len(query_tokens & text_tokens)
        return min(1.0, overlap / max(len(query_tokens), 1))

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer with stopword removal."""
        _STOPWORDS = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "and", "or", "but", "not", "so", "if", "than", "that", "this",
            "it", "its", "i", "me", "my", "you", "your", "we", "our",
            "they", "them", "their", "what", "which", "who", "how",
        }
        words = re.findall(r"\b[a-z]+\b", (text or "").lower())
        return [w for w in words if w not in _STOPWORDS and len(w) > 2]
