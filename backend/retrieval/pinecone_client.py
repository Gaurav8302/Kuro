"""Pinecone implementation of VectorStoreClient abstraction."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from .base import RetrievedChunk, VectorStoreClient


class PineconeVectorClient(VectorStoreClient):  # type: ignore[misc]
    def __init__(self, index, embed_fn):
        self.index = index
        self._embed_fn = embed_fn

    def embed(self, text: str):  # pragma: no cover - pass-through
        return self._embed_fn(text)

    def similarity_search(
        self,
        query: str,
        top_k: int,
        user_filter: Optional[str] = None,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        filt = filter or {}
        if user_filter:
            filt["user"] = user_filter
        vector = self.embed(query)
        kwargs = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
        }
        if filt:
            kwargs["filter"] = filt
        if namespace:
            kwargs["namespace"] = namespace
        try:
            res = self.index.query(**kwargs)
        except Exception:
            return []
        out: List[RetrievedChunk] = []
        for m in getattr(res, "matches", []) or []:
            md = m.metadata or {}
            out.append(
                RetrievedChunk(
                    id=getattr(m, "id", md.get("id") or "unknown"),
                    text=md.get("text", ""),
                    metadata=md,
                    similarity=float(getattr(m, "score", 0.0)),
                    source=md.get("source", "memory"),
                )
            )
        return out


__all__ = ["PineconeVectorClient"]
