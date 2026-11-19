"""Embedding configuration for Kuro memory / RAG.

Current provider: Google Gemini Embedding API
Model: gemini-embedding-001 (stable text embeddings)
Dimension: Dynamic / Auto-detected from connected Pinecone index (defaults to 768 or KURO_EMBEDDING_DIMENSION)
"""
from __future__ import annotations

import math
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Stable Gemini text embedding model (replacement for retired text-embedding-004).
EMBEDDING_MODEL = os.getenv("KURO_EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBEDDING_DIMENSION = int(os.getenv("KURO_EMBEDDING_DIMENSION", "768"))
EMBEDDING_METRIC = os.getenv("KURO_EMBEDDING_METRIC", "cosine")
DEFAULT_PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "kuro-memory")

_active_embedding_dimension: Optional[int] = None


def get_embedding_dimension() -> int:
    """Get active embedding dimension, respecting index auto-detection or environment overrides."""
    global _active_embedding_dimension
    if _active_embedding_dimension is not None:
        return _active_embedding_dimension
    env_dim = os.getenv("KURO_EMBEDDING_DIMENSION")
    if env_dim and env_dim.isdigit():
        return int(env_dim)
    return EMBEDDING_DIMENSION


def set_embedding_dimension(dim: int) -> None:
    """Set active embedding dimension to match the connected Pinecone index."""
    global _active_embedding_dimension, EMBEDDING_DIMENSION
    if dim and dim > 0:
        _active_embedding_dimension = dim
        EMBEDDING_DIMENSION = dim
        logger.info("Active embedding dimension configured to %d to match Pinecone index", dim)


def normalize_embedding(vector: List[float]) -> List[float]:
    """L2-normalize embedding vector (required for cosine similarity)."""
    if not vector:
        return vector
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero embedding vector")
    return [v / norm for v in vector]


def validate_embedding_dimension(
    vector: List[float],
    *,
    context: str = "embedding",
    expected_dim: Optional[int] = None,
) -> List[float]:
    target_dim = expected_dim or get_embedding_dimension()
    if len(vector) != target_dim:
        raise ValueError(
            f"{context} dimension mismatch: got {len(vector)}, "
            f"expected {target_dim} for {EMBEDDING_MODEL}"
        )
    return vector


__all__ = [
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_METRIC",
    "DEFAULT_PINECONE_INDEX",
    "get_embedding_dimension",
    "set_embedding_dimension",
    "normalize_embedding",
    "validate_embedding_dimension",
]
