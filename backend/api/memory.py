"""
Memory API Router — Memory management endpoints

Provides store-memory, retrieve-memory endpoints.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Memory"])


class MemoryInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    text: str = Field(..., description="Text content to store")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, description="Number of results")


@router.post("/store-memory")
def store_user_memory(payload: MemoryInput):
    """Store user memory in the vector database."""
    try:
        from memory.ultra_lightweight_memory import store_memory
        payload.metadata["user"] = payload.user_id
        memory_id = store_memory(payload.text, payload.metadata)
        return {"status": "success", "memory_id": memory_id}
    except Exception as e:
        logger.error("Error storing memory: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve-memory")
def retrieve_memories(payload: QueryInput):
    """Retrieve relevant memories via semantic search."""
    try:
        from memory.ultra_lightweight_memory import get_relevant_memories_detailed
        memories = get_relevant_memories_detailed(
            query=payload.query,
            user_filter=payload.user_id,
            top_k=payload.top_k,
        )
        formatted = [
            {
                "text": m["text"],
                "score": m.get("score", 0.0),
                "importance": m.get("importance", 0.5),
                "category": m.get("category", "general"),
                "timestamp": m.get("timestamp", ""),
            }
            for m in memories
        ]
        return {"query": payload.query, "results": formatted}
    except Exception as e:
        logger.error("Error retrieving memories: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
