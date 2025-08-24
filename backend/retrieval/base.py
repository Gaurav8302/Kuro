"""Base abstractions for the RAG retrieval layer.

These abstractions allow swapping underlying vector stores (Pinecone, Weaviate,
FAISS, etc.) and keyword / tag indexes without changing the pipeline logic.

All implementations must be side-effect free (pure) except for explicit
`add_document` operations to keep them unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, List, Dict, Any, Optional


@dataclass
class RetrievedChunk:
    """Container for a retrieved knowledge chunk prior to final ranking.

    Attributes:
        id: Unique identifier (stable across stores if possible)
        text: Raw text content
        metadata: Arbitrary metadata dictionary
        similarity: Raw similarity score from vector store (higher = more similar)
        keyword_score: Optional keyword / lexical relevance score
        source: Source identifier (e.g. "memory", "doc", "faq")
    """
    id: str
    text: str
    metadata: Dict[str, Any]
    similarity: float = 0.0
    keyword_score: float = 0.0
    source: str = "unknown"


class VectorStoreClient(Protocol):
    """Protocol describing vector similarity operations required by the pipeline."""

    def similarity_search(
        self,
        query: str,
        top_k: int,
        user_filter: Optional[str] = None,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Return top_k semantically similar chunks.

        Implementations SHOULD populate: id, text, metadata, similarity, source.
        Keyword score can remain default (0.0) and will be filled by lexical stage.
        """
        ...

    def embed(self, text: str) -> List[float]:  # pragma: no cover - pass-through
        """(Optional) Provide access to embedding generation for advanced refinement."""
        ...


class KeywordIndex(Protocol):
    """Protocol for a light-weight lexical / tag index."""

    def add_document(self, id: str, text: str, metadata: Dict[str, Any]):
        ...

    def keyword_search(
        self,
        query: str,
        top_k: int,
        user_filter: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        ...


class InMemoryKeywordIndex:
    """Simple in-memory keyword index using TF-IDF like scoring (light-weight).

    NOT intended for large-scale production but perfectly adequate for
    unit tests and local development. Can be replaced with BM25 / Elastic easily.
    """

    def __init__(self):
        self._docs: Dict[str, Dict[str, Any]] = {}
        self._token_freq: Dict[str, Dict[str, int]] = {}
        self._df: Dict[str, int] = {}
        self._total_docs = 0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        import re
        # Allow alphanumeric + basic punctuation separation; lower-case.
        cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", text.lower())
        return [t for t in cleaned.split() if t]

    def add_document(self, id: str, text: str, metadata: Dict[str, Any]):  # type: ignore[override]
        if id in self._docs:
            return  # idempotent
        tokens = self._tokenize(text)
        tf: Dict[str, int] = {}
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1
        self._docs[id] = {"text": text, "metadata": metadata, "tf": tf}
        for tok in tf.keys():
            self._df[tok] = self._df.get(tok, 0) + 1
        self._total_docs += 1
        self._token_freq[id] = tf

    def keyword_search(self, query: str, top_k: int, user_filter: Optional[str] = None):  # type: ignore[override]
        if not self._docs:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        import math
        scores: Dict[str, float] = {}
        for doc_id, doc in self._docs.items():
            if user_filter and doc["metadata"].get("user") != user_filter:
                continue
            tf = doc["tf"]
            score = 0.0
            for tok in tokens:
                if tok in tf:
                    # tf-idf weight (1 + log(tf)) * log(N / df)
                    df = self._df.get(tok, 1)
                    idf = math.log((self._total_docs + 1) / (df + 1)) + 1
                    score += (1 + math.log(tf[tok])) * idf
            if score > 0:
                scores[doc_id] = score
        # Build RetrievedChunk list
        results: List[RetrievedChunk] = []
        for doc_id, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True)[: top_k]:
            doc = self._docs[doc_id]
            results.append(
                RetrievedChunk(
                    id=doc_id,
                    text=doc["text"],
                    metadata=doc["metadata"],
                    keyword_score=sc,
                    source=doc["metadata"].get("source", "memory"),
                )
            )
        return results


__all__ = [
    "RetrievedChunk",
    "VectorStoreClient",
    "KeywordIndex",
    "InMemoryKeywordIndex",
]
