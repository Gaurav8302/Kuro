"""Advanced multi-pass RAG pipeline implementation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import logging
import re

from .base import VectorStoreClient, KeywordIndex, RetrievedChunk
from .ranking import rank_chunks, RankingWeights
from .formatter import dedupe_chunks, format_context

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    top_k_broad: int = 20
    top_k_keyword: int = 12
    top_k_focus_candidates: int = 12
    top_k_final: int = 8
    focus_pass_multiplier: float = 1.5  # broaden second vector search
    ranking_weights: RankingWeights = field(default_factory=RankingWeights)
    source_reliability: Dict[str, float] = field(
        default_factory=lambda: {
            "user_profile": 0.95,
            "faq": 0.9,
            "memory": 0.7,
            "chat_exchange": 0.6,
            "unknown": 0.5,
        }
    )
    max_context_chars: int = 3500


class RAGPipeline:
    def __init__(
        self,
        vector_client: VectorStoreClient,
        keyword_index: KeywordIndex,
        config: Optional[RAGConfig] = None,
    ):
        self.vector_client = vector_client
        self.keyword_index = keyword_index
        self.config = config or RAGConfig()

    @staticmethod
    def _sanitize_query(q: str) -> str:
        # Prevent injection / prompt leakage in lexical layer by stripping control chars
        return re.sub(r"[\r\n\t]", " ", q)[:2000]

    def retrieve(
        self,
        query: str,
        user_id: Optional[str] = None,
        user_pref_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        q = self._sanitize_query(query)
        cfg = self.config
        logger.debug(f"RAG retrieval start query='{q}' user='{user_id}'")

        # Pass 1: Broad vector + keyword retrieval (union)
        vector_results = self.vector_client.similarity_search(
            q, top_k=cfg.top_k_broad, user_filter=user_id
        )
        keyword_results = self.keyword_index.keyword_search(
            q, top_k=cfg.top_k_keyword, user_filter=user_id
        )
        merged: Dict[str, RetrievedChunk] = {}
        for c in vector_results + keyword_results:
            if c.id in merged:
                # Merge scores (keep max to avoid dilution)
                existing = merged[c.id]
                existing.similarity = max(existing.similarity, c.similarity)
                existing.keyword_score = max(existing.keyword_score, c.keyword_score)
            else:
                merged[c.id] = c
        broad_chunks = list(merged.values())
        logger.debug(f"Pass1 broad_chunks={len(broad_chunks)}")

        # Select focus candidates preliminarily (by simple combined interim score)
        prelim_rank = sorted(
            broad_chunks,
            key=lambda c: (c.similarity + c.keyword_score * 0.7),
            reverse=True,
        )[: cfg.top_k_focus_candidates]

        # Build refined query (simple enrichment with top categories / tags)
        enrichment_terms = []
        for c in prelim_rank[:5]:
            cat = c.metadata.get("category")
            if cat:
                enrichment_terms.append(cat)
            for tag in c.metadata.get("tags", [])[:2]:
                enrichment_terms.append(str(tag))
        refined_query = q + " " + " ".join(set(enrichment_terms))

        # Pass 2: Focused vector search (optional if we had any prelim results)
        focus_results: List[RetrievedChunk] = []
        if prelim_rank:
            focus_k = int(cfg.top_k_broad * cfg.focus_pass_multiplier)
            focus_results = self.vector_client.similarity_search(
                refined_query, top_k=focus_k, user_filter=user_id
            )
            # Merge again
            for c in focus_results:
                if c.id in merged:
                    existing = merged[c.id]
                    existing.similarity = max(existing.similarity, c.similarity)
                else:
                    merged[c.id] = c
        all_chunks = list(merged.values())
        logger.debug(
            f"Pass2 focus_results={len(focus_results)} total_after_merge={len(all_chunks)}"
        )

        # Final ranking
        ranked = rank_chunks(
            all_chunks,
            weights=cfg.ranking_weights,
            source_reliability=cfg.source_reliability,
            user_pref_tags=user_pref_tags,
        )
        ranked = ranked[: cfg.top_k_final]
        ranked = dedupe_chunks(ranked)
        context_str = format_context(ranked, max_chars=cfg.max_context_chars)

        logger.info(
            "RAG retrieval complete: query='%s' broad=%d focus=%d final=%d",  # noqa: E501
            q,
            len(broad_chunks),
            len(focus_results),
            len(ranked),
        )
        return {
            "query": q,
            "refined_query": refined_query,
            "broad_count": len(broad_chunks),
            "focus_count": len(focus_results),
            "final_chunks": ranked,
            "context": context_str,
        }


__all__ = ["RAGPipeline", "RAGConfig"]
