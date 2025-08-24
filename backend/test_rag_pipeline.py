"""Basic tests for the RAG pipeline components.

These tests focus on ensuring the hybrid merging, ranking, and formatting work
without requiring live Pinecone responses (we stub the vector client).
"""

from retrieval.pipeline import RAGPipeline, RAGConfig
from retrieval.base import RetrievedChunk, InMemoryKeywordIndex, VectorStoreClient
from retrieval.ranking import RankingWeights


class StubVector(VectorStoreClient):  # type: ignore[misc]
    def __init__(self, data):
        self.data = data

    def similarity_search(self, query, top_k, user_filter=None, namespace=None, filter=None):
        # Return data with decreasing similarity
        out = []
        for i, item in enumerate(self.data[: top_k]):
            out.append(
                RetrievedChunk(
                    id=f"vec-{i}",
                    text=item["text"],
                    metadata=item.get("metadata", {}),
                    similarity=1.0 - i * 0.05,
                    source=item.get("metadata", {}).get("source", "memory"),
                )
            )
        return out

    def embed(self, text: str):  # pragma: no cover - not needed
        return [0.0]


def test_rag_basic_merge():
    vec_data = [
        {"text": "User likes Python", "metadata": {"category": "preferences", "timestamp": "2025-01-01T00:00:00"}},
        {"text": "User is named Alice", "metadata": {"category": "user_profile", "timestamp": "2025-02-01T00:00:00"}},
    ]
    vector_client = StubVector(vec_data)
    kw_index = InMemoryKeywordIndex()
    kw_index.add_document("k1", "Python preferences and coding", {"category": "preferences"})
    kw_index.add_document("k2", "Profile: Alice enjoys AI", {"category": "user_profile"})

    pipeline = RAGPipeline(vector_client, kw_index, RAGConfig(top_k_broad=5, top_k_keyword=5, top_k_final=4))
    result = pipeline.retrieve("What does Alice like?", user_id=None)

    assert result["final_chunks"], "Expected some final chunks"
    assert result["context"].startswith("-"), "Context should be bullet formatted"


if __name__ == "__main__":  # Manual run
    test_rag_basic_merge()
    print("RAG pipeline basic test passed")
