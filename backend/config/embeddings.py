"""Embedding configuration for Kuro memory / RAG.

Current provider: Google Gemini Embedding API
Model: gemini-embedding-001 (stable text embeddings)
Dimension: 768 (recommended Matryoshka size; must match Pinecone index)

Do not truncate/pad vectors to force a mismatch. If the embedding length
does not equal EMBEDDING_DIMENSION, fail clearly.
"""
from __future__ import annotations

import math
import os
from typing import List

# Stable Gemini text embedding model (replacement for retired text-embedding-004).
EMBEDDING_MODEL = os.getenv("KURO_EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBEDDING_DIMENSION = int(os.getenv("KURO_EMBEDDING_DIMENSION", "768"))
EMBEDDING_METRIC = os.getenv("KURO_EMBEDDING_METRIC", "cosine")

# Clean index for the current embedding space. Demo vectors from the old
# 384-d sliced text-embedding-004 index are disposable.
DEFAULT_PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "kuro-memory")


def normalize_embedding(vector: List[float]) -> List[float]:
    """L2-normalize non-3072 gemini-embedding-001 vectors (required by Google)."""
    if not vector:
        return vector
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero embedding vector")
    return [v / norm for v in vector]


def validate_embedding_dimension(vector: List[float], *, context: str = "embedding") -> List[float]:
    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"{context} dimension mismatch: got {len(vector)}, "
            f"expected {EMBEDDING_DIMENSION} for {EMBEDDING_MODEL}"
        )
    return vector


__all__ = [
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_METRIC",
    "DEFAULT_PINECONE_INDEX",
    "normalize_embedding",
    "validate_embedding_dimension",
]
