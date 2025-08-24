"""Retrieval package exposing a pluggable RAG pipeline.

The pipeline is instantiated lazily to avoid circular imports with the legacy
memory manager. Import `get_rag_pipeline()` to obtain a singleton instance.
"""

from __future__ import annotations
from typing import Optional
import os
import time
from .pipeline import RAGPipeline, RAGConfig
from .base import InMemoryKeywordIndex
from .pinecone_client import PineconeVectorClient
import logging

_rag_pipeline: Optional[RAGPipeline] = None
_index_empty: Optional[bool] = None
_last_index_check: float = 0.0
_INDEX_CHECK_INTERVAL = int(os.getenv("RAG_INDEX_CHECK_INTERVAL", "300"))  # seconds
logger = logging.getLogger(__name__)


def _check_index_ready(pipeline: RAGPipeline) -> bool:
    """Lightweight readiness check with memoization.

    We avoid calling Pinecone stats on every request by caching result for a TTL.
    If index appears empty (zero vectors) we mark and skip retrieval to save latency/cost.
    """
    global _index_empty, _last_index_check
    now = time.time()
    if _index_empty is not None and (now - _last_index_check) < _INDEX_CHECK_INTERVAL:
        return not _index_empty
    try:
        # Attempt to infer emptiness using a very cheap similarity_search on a nonsense token
        probe = pipeline.vector_client.similarity_search("__probe__", top_k=1)
        _index_empty = len(probe) == 0
        _last_index_check = now
        if _index_empty:
            logger.info("RAG index appears empty (probe returned 0). Retrieval will be skipped until populated.")
        else:
            logger.info("RAG index readiness confirmed (has vectors).")
    except Exception as e:  # pragma: no cover
        logger.warning(f"RAG index readiness probe failed: {e}")
        # Fail open (assume ready) to avoid permanent disablement
        _index_empty = False
        _last_index_check = now
    return not _index_empty


def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        try:
            # Local import to avoid circular when memory manager imports retrieval
            from memory.ultra_lightweight_memory import ultra_lightweight_memory_manager

            vector_client = PineconeVectorClient(
                ultra_lightweight_memory_manager.index,
                ultra_lightweight_memory_manager.get_embedding,
            )
            keyword_index = InMemoryKeywordIndex()
            _rag_pipeline = RAGPipeline(vector_client, keyword_index, RAGConfig())
            logger.info("Initialized global RAG pipeline")
            # Initial readiness probe (non-fatal)
            _check_index_ready(_rag_pipeline)
        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Failed to initialize RAG pipeline: {e}")
            raise
    return _rag_pipeline


def rag_retrieval_enabled() -> bool:
    """Public helper to determine if retrieval should run.

    Returns False quickly if index known empty within recent TTL window.
    """
    try:
        pipeline = get_rag_pipeline()
        return _check_index_ready(pipeline)
    except Exception:
        return False


def ingest_document(id: str, text: str, metadata):
    """Add document to keyword index (safe no-op if pipeline missing)."""
    try:
        pipeline = get_rag_pipeline()
        pipeline.keyword_index.add_document(id, text, metadata)
    except Exception:  # pragma: no cover - avoid breaking primary path
        pass


__all__ = ["get_rag_pipeline", "ingest_document", "rag_retrieval_enabled"]
