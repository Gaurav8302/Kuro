from database.db import get_collection
from bson.objectid import ObjectId
from datetime import datetime
from db.pinecone import upsert_vector

def memories_collection():
    return get_collection("memories_v3")

def insert_memory(memory):
    memory["created_at"] = datetime.utcnow()
    # Ensure memory['content'] exists
    inserted_id = memories_collection().insert_one(memory).inserted_id
    # sync to pinecone
    upsert_vector(
        vec_id=str(inserted_id),
        text=memory.get("content", ""),
        user_id=memory.get("user_id"),
        memory_type=memory.get("type"),
        importance=memory.get("importance", 5)
    )
    return inserted_id

def find_similar_memory(content, user_id=None):
    # Quick text match for similarity simulation before embedding logic
    query = {"content": content}
    if user_id:
        query["user_id"] = user_id
    return memories_collection().find_one(query)

def update_memory(memory_id, new_data):
    new_data["updated_at"] = datetime.utcnow()
    obj_id = ObjectId(memory_id) if isinstance(memory_id, str) else memory_id
    memories_collection().update_one(
        {"_id": obj_id},
        {"$set": new_data}
    )
    
    # query to get full data for pinecone upsert
    updated_doc = memories_collection().find_one({"_id": obj_id})
    if updated_doc:
        upsert_vector(
            vec_id=str(updated_doc["_id"]),
            text=updated_doc.get("content", ""),
            user_id=updated_doc.get("user_id"),
            memory_type=updated_doc.get("type"),
            importance=updated_doc.get("importance", 5)
        )
