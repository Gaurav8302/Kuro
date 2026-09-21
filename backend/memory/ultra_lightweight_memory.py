"""
Ultra-lightweight memory manager.
Uses Gemini gemini-embedding-001 @ 768-d via db.pinecone.embed_text.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import math

from config.embeddings import DEFAULT_PINECONE_INDEX, EMBEDDING_DIMENSION, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class UltraLightweightMemoryManager:
    """Memory manager optimized for minimal memory usage"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for embeddings")

        self.embedding_model = EMBEDDING_MODEL
        self.embedding_dimension = EMBEDDING_DIMENSION

        from pinecone import Pinecone

        pc_api_key = os.getenv("PINECONE_API_KEY")
        if not pc_api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")

        try:
            self.pc = Pinecone(api_key=pc_api_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", DEFAULT_PINECONE_INDEX)
            logger.info("Connecting to Pinecone index: %s (%sd)", index_name, EMBEDDING_DIMENSION)
            self.index = self.pc.Index(index_name)
            logger.info("Ultra-lightweight memory manager initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Pinecone connection: %s", e)
            raise

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Gemini. Never returns a zero/padded fake vector."""
        from db.pinecone import embed_text

        return embed_text(text, task_type="retrieval_document")

    def store_memory(self, text: str, metadata: Dict[str, Any], importance: Optional[float] = None) -> str:
        try:
            embedding = self.get_embedding(text)
            import uuid

            memory_id = str(uuid.uuid4())
            memory_metadata = {
                **(metadata or {}),
                "text": text,
                "importance": float(importance) if importance is not None else 0.5,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dim": EMBEDDING_DIMENSION,
            }
            self.index.upsert(vectors=[(memory_id, embedding, memory_metadata)])
            logger.info("Stored memory %s", memory_id)
            return memory_id
        except Exception as e:
            logger.error("Error storing memory: %s", e)
            raise

    def get_relevant_memories(self, query: str, user_filter: Optional[str] = None, top_k: int = 5) -> List[str]:
        detailed = self.get_relevant_memories_detailed(query, user_filter, top_k)
        return [m["text"] for m in detailed if m.get("text")]

    def get_relevant_memories_detailed(
        self, query: str, user_filter: Optional[str] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        try:
            from db.pinecone import embed_text

            query_embedding = embed_text(query, task_type="retrieval_query")
            filter_dict = {"user_id": {"$eq": user_filter}} if user_filter else None
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict,
            )
            memories = []
            for match in results.matches:
                meta = dict(match.metadata or {})
                memories.append(
                    {
                        "text": meta.get("text") or meta.get("content", ""),
                        "score": float(match.score or 0.0),
                        "importance": meta.get("importance", 0.5),
                        "category": meta.get("category", "general"),
                        "timestamp": meta.get("timestamp", ""),
                    }
                )
            return memories
        except Exception as e:
            logger.error("Error retrieving memories: %s", e)
            raise

    def get_user_context(self, user_id: str):
        return {"recent_memories": 0, "topics": [], "last_interaction": ""}

    def cleanup_old_memories(self, user_id: str, days_threshold: int = 30):
        logger.info("Cleanup requested for user %s (threshold: %s days)", user_id, days_threshold)
        return True


if os.getenv("DISABLE_MEMORY_INIT") == "1":

    class _DummyMemoryManager:
        index = None

        def store_memory(self, *args, **kwargs):
            import uuid
            return str(uuid.uuid4())

        def get_relevant_memories(self, *args, **kwargs):
            return []

        def get_relevant_memories_detailed(self, *args, **kwargs):
            return []

        def get_user_context(self, user_id: str):
            return {"recent_memories": 0, "topics": [], "last_interaction": ""}

        def cleanup_old_memories(self, user_id: str, days_threshold: int = 30):
            return True

        def get_embedding(self, text: str):
            return [0.0] * EMBEDDING_DIMENSION

    ultra_lightweight_memory_manager = _DummyMemoryManager()
    logger.info("Using dummy memory manager (DISABLE_MEMORY_INIT=1)")
else:
    try:
        ultra_lightweight_memory_manager = UltraLightweightMemoryManager()
    except Exception as e:
        logger.error("Ultra-lightweight memory init failed: %s", e)

        class _DummyMemoryManager:
            index = None

            def store_memory(self, *args, **kwargs):
                raise RuntimeError("Memory manager unavailable")

            def get_relevant_memories(self, *args, **kwargs):
                return []

            def get_relevant_memories_detailed(self, *args, **kwargs):
                return []

            def get_user_context(self, user_id: str):
                return {"recent_memories": 0, "topics": [], "last_interaction": ""}

            def cleanup_old_memories(self, user_id: str, days_threshold: int = 30):
                return True

            def get_embedding(self, text: str):
                raise RuntimeError("Memory manager unavailable")

        ultra_lightweight_memory_manager = _DummyMemoryManager()


def store_memory(text: str, metadata: Dict[str, Any], importance: Optional[float] = None) -> str:
    return ultra_lightweight_memory_manager.store_memory(text, metadata, importance)


def get_relevant_memories(query: str, user_filter: Optional[str] = None, top_k: int = 5) -> List[str]:
    return ultra_lightweight_memory_manager.get_relevant_memories(query, user_filter, top_k)


def get_relevant_memories_detailed(
    query: str, user_filter: Optional[str] = None, top_k: int = 5
) -> List[Dict[str, Any]]:
    return ultra_lightweight_memory_manager.get_relevant_memories_detailed(query, user_filter, top_k)
