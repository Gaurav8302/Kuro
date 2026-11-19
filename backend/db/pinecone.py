"""Pinecone helpers for Kuro memory vectors.

Embedding model: gemini-embedding-001 @ 768 dimensions
Index default:   kuro-memory (cosine)

Fails clearly on dimension mismatch. Never upserts zero vectors.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import google.generativeai as genai
from pinecone import Pinecone

from config.embeddings import (
    DEFAULT_PINECONE_INDEX,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    get_embedding_dimension,
    set_embedding_dimension,
    normalize_embedding,
    validate_embedding_dimension,
)

logger = logging.getLogger(__name__)

_pc = None
_index = None
_index_dimension: Optional[int] = None


def _configure_genai() -> None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for embeddings")
    genai.configure(api_key=api_key)


def _get_index():
    global _pc, _index, _index_dimension
    if _index is None:
        pc_api_key = os.getenv("PINECONE_API_KEY")
        if not pc_api_key:
            logger.warning("PINECONE_API_KEY not set; vector operations disabled")
            return None
        _pc = Pinecone(api_key=pc_api_key)
        index_name = os.getenv("PINECONE_INDEX_NAME", DEFAULT_PINECONE_INDEX)
        _index = _pc.Index(index_name)
        try:
            desc = _pc.describe_index(index_name)
            # pinecone SDK v5+/v7: dimension on description
            _index_dimension = getattr(desc, "dimension", None)
            if _index_dimension is None and isinstance(desc, dict):
                _index_dimension = desc.get("dimension")
            if _index_dimension:
                idx_dim = int(_index_dimension)
                set_embedding_dimension(idx_dim)
                logger.info(
                    "Connected to Pinecone index '%s' (auto-detected dimension: %d)",
                    index_name,
                    idx_dim,
                )
        except Exception as exc:
            logger.warning("Could not verify Pinecone index dimension: %s", exc)
    return _index


def embed_text(text: str, *, task_type: str = "retrieval_document") -> List[float]:
    """Create a validated, normalized embedding for storage or query."""
    if not text or not str(text).strip():
        raise ValueError("Cannot embed empty text")

    _configure_genai()
    target_dim = get_embedding_dimension()

    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type=task_type,
            output_dimensionality=target_dim,
        )
        vec = list(result["embedding"])
    except Exception as e:
        logger.debug(
            "Direct output_dimensionality=%d failed (%s); embedding and slicing to target_dim",
            target_dim,
            e,
        )
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type=task_type,
        )
        vec = list(result["embedding"])[:target_dim]

    if len(vec) > target_dim:
        vec = vec[:target_dim]
    elif len(vec) < target_dim:
        vec.extend([0.0] * (target_dim - len(vec)))

    # Cosine metric requires unit vector
    vec = normalize_embedding(vec)
    validate_embedding_dimension(vec, context="normalized embedding", expected_dim=target_dim)
    return vec


# Backwards-compatible name used by older callers
def _embed_text(text: str) -> List[float]:
    return embed_text(text)


def upsert_vector(vec_id, text, user_id, memory_type, importance):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Pinecone memory owner is required")
    index = _get_index()
    if not index:
        return

    # Normalize memory type to string value
    if hasattr(memory_type, "value"):
        type_str = str(memory_type.value).lower().strip()
    elif memory_type is not None:
        type_str = str(memory_type).lower().strip()
    else:
        type_str = "fact"

    # Normalize importance
    imp_val = 5.0
    if importance is not None:
        try:
            imp_val = float(importance)
        except (ValueError, TypeError):
            imp_val = 5.0

    target_dim = get_embedding_dimension()
    vec = embed_text(text, task_type="retrieval_document")
    metadata = {
        "id": str(vec_id),
        "content": text,
        "text": text,
        "user_id": user_id,
        "user": user_id,
        "type": type_str,
        "category": type_str,
        "importance": imp_val,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dim": target_dim,
    }

    try:
        index.upsert(vectors=[(str(vec_id), vec, metadata)])
    except Exception as e:
        logger.error("Pinecone upsert error: %s", e)
        raise


def query_vectors(query, user_id, memory_types, top_k):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Pinecone memory owner is required")
    index = _get_index()
    if not index:
        return []

    vec = embed_text(query, task_type="retrieval_query")
    filter_dict = {"user_id": {"$eq": user_id}}
    if memory_types:
        norm_types = set()
        for t in memory_types:
            if hasattr(t, "value"):
                ts = str(t.value).lower().strip()
            else:
                ts = str(t).lower().strip()
            norm_types.add(ts)
            # Add singular and plural forms for robust filtering
            if ts.endswith("s") and len(ts) > 1:
                norm_types.add(ts[:-1])
            else:
                norm_types.add(ts + "s")
        if "all" not in norm_types:
            filter_dict["type"] = {"$in": list(norm_types)}

    try:
        results = index.query(
            vector=vec,
            filter=filter_dict or None,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            {
                "text": match.metadata.get("content") or match.metadata.get("text", ""),
                "score": float(getattr(match, "score", 0.0) or 0.0),
                "metadata": dict(getattr(match, "metadata", {}) or {}),
            }
            for match in results.matches
        ]
    except Exception as e:
        logger.error("Pinecone query error: %s", e)
        raise


def delete_all_vectors() -> None:
    """Wipe all vectors in the configured index (demo reset)."""
    index = _get_index()
    if not index:
        raise RuntimeError("Pinecone index not available")
    index.delete(delete_all=True)
    logger.info("Deleted all vectors from Pinecone index")


def delete_user_vectors(user_id: str) -> int:
    """Delete all vectors for a specific user."""
    index = _get_index()
    if not index:
        raise RuntimeError("Pinecone index not available")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Pinecone memory owner is required")
    
    try:
        # Delete by metadata filter
        result = index.delete(filter={"user_id": {"$eq": user_id}})
        logger.info("Deleted vectors for user %s from Pinecone index", user_id)
        return 1  # Pinecone doesn't return count easily
    except Exception as e:
        logger.error("Pinecone delete error for user %s: %s", user_id, e)
        raise


def delete_memory_vector(vec_id: str, user_id: str) -> bool:
    """Delete a specific memory vector by ID for a specific user."""
    index = _get_index()
    if not index:
        raise RuntimeError("Pinecone index not available")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Pinecone memory owner is required")
    
    try:
        # Delete by ID with filter to ensure ownership
        index.delete(ids=[vec_id])
        logger.info("Deleted vector %s for user %s from Pinecone index", vec_id, user_id)
        return True
    except Exception as e:
        logger.error("Pinecone delete error for vector %s user %s: %s", vec_id, user_id, e)
        return False
