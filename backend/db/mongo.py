from database.db import get_collection
from bson.objectid import ObjectId
from datetime import datetime
import logging
from db.pinecone import upsert_vector, query_vectors

logger = logging.getLogger(__name__)

def memories_collection():
    return get_collection("memories_v3")

def insert_memory(memory):
    user_id = memory.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Memory owner is required")
    memory["created_at"] = datetime.utcnow()
    
    # Normalize type across schemas
    raw_type = memory.get("memory_type") or memory.get("type") or "fact"
    if hasattr(raw_type, "value"):
        type_str = str(raw_type.value).lower().strip()
    else:
        type_str = str(raw_type).lower().strip()
    memory["type"] = type_str
    memory["memory_type"] = type_str

    inserted_id = memories_collection().insert_one(memory).inserted_id
    
    # Sync to pinecone safely
    try:
        upsert_vector(
            vec_id=str(inserted_id),
            text=memory.get("content", ""),
            user_id=user_id,
            memory_type=type_str,
            importance=memory.get("importance", 5)
        )
    except Exception as e:
        logger.error("Failed to sync new memory %s to Pinecone: %s", inserted_id, e)

    return inserted_id

def find_similar_memory_semantic(content, user_id, memory_types=None, min_score=0.85):
    results = query_vectors(
        query=content,
        user_id=user_id,
        memory_types=memory_types,
        top_k=1,
    )
    if not results:
        return None

    best = results[0]
    if best.get("score", 0.0) < min_score:
        return None

    meta = best.get("metadata", {})
    memory_id = meta.get("id")
    if not memory_id:
        return None

    doc = memories_collection().find_one({"_id": ObjectId(memory_id), "user_id": user_id})
    if not doc:
        return None

    doc["similarity"] = best.get("score", 0.0)
    return doc

def update_memory(memory_id, new_data, user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Memory owner is required")
    new_data["updated_at"] = datetime.utcnow()

    if "memory_type" in new_data or "type" in new_data:
        raw_type = new_data.get("memory_type") or new_data.get("type") or "fact"
        type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type).lower().strip()
        new_data["type"] = type_str
        new_data["memory_type"] = type_str

    obj_id = ObjectId(memory_id) if isinstance(memory_id, str) else memory_id
    memories_collection().update_one(
        {"_id": obj_id, "user_id": user_id},
        {"$set": new_data}
    )
    
    # query to get full data for pinecone upsert
    updated_doc = memories_collection().find_one({"_id": obj_id, "user_id": user_id})
    if updated_doc:
        raw_type = updated_doc.get("memory_type") or updated_doc.get("type") or "fact"
        type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type).lower().strip()
        try:
            upsert_vector(
                vec_id=str(updated_doc["_id"]),
                text=updated_doc.get("content", ""),
                user_id=updated_doc.get("user_id"),
                memory_type=type_str,
                importance=updated_doc.get("importance", 5)
            )
        except Exception as e:
            logger.error("Failed to sync updated memory %s to Pinecone: %s", memory_id, e)


def reinforce_memories(memory_ids, user_id):
    for memory_id in memory_ids:
        try:
            obj_id = ObjectId(memory_id) if isinstance(memory_id, str) else memory_id
            doc = memories_collection().find_one({"_id": obj_id, "user_id": user_id})
            if not doc:
                continue
            new_importance = float(doc.get("importance", 0.0)) + 1.0
            update_memory(obj_id, {"importance": new_importance}, user_id)
        except Exception:
            continue


def delete_memory(memory_id: str, user_id: str) -> bool:
    """Delete a specific memory by ID for a specific user."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Memory owner is required")
    obj_id = ObjectId(memory_id) if isinstance(memory_id, str) else memory_id
    result = memories_collection().delete_one({"_id": obj_id, "user_id": user_id})
    if result.deleted_count > 0:
        # Also delete from Pinecone
        from db.pinecone import delete_memory_vector
        try:
            delete_memory_vector(str(obj_id), user_id)
        except Exception as e:
            logger.warning("Failed to delete vector for memory %s: %s", memory_id, e)
        return True
    return False


def delete_user_memories(user_id: str) -> int:
    """Delete all memories for a specific user (for account deletion)."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Memory owner is required")
    result = memories_collection().delete_many({"user_id": user_id})
    if result.deleted_count > 0:
        # Also delete from Pinecone
        from db.pinecone import delete_user_vectors
        try:
            delete_user_vectors(user_id)
        except Exception as e:
            logger.warning("Failed to delete vectors for user %s: %s", user_id, e)
    return result.deleted_count
