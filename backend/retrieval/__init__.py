"""Retrieval package exposing a pluggable RAG pipeline.

The pipeline is instantiated lazily to avoid circular imports with the legacy
memory manager. Import `get_rag_pipeline()` to obtain a singleton instance.
"""

from __future__ import annotations
from typing import Optional
from .pipeline import RAGPipeline, RAGConfig
from .base import InMemoryKeywordIndex
from .pinecone_client import PineconeVectorClient
import logging

_rag_pipeline: Optional[RAGPipeline] = None
logger = logging.getLogger(__name__)


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
        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Failed to initialize RAG pipeline: {e}")
            raise
    return _rag_pipeline


def ingest_document(id: str, text: str, metadata):
    """Add document to keyword index (safe no-op if pipeline missing)."""
    try:
        pipeline = get_rag_pipeline()
        pipeline.keyword_index.add_document(id, text, metadata)
    except Exception:  # pragma: no cover - avoid breaking primary path
        pass


__all__ = ["get_rag_pipeline", "ingest_document"]
