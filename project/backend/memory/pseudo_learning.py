"""Pseudo-Learning system for Kuro AI.

Stores user corrections / verified facts and applies them in future answers
without model retraining.

Data model (MongoDB collection: user_corrections):
  {
    _id,
    user_id,
    original_question,
    original_answer,
    correction_text,
    tags: [str],
    hash: sha256(original_question + correction_text),
    created_at,
    last_used_at,
    usage_count: int
  }

Embeddings: stored in Pinecone via existing embedding pathway. Each correction
is also inserted as a vector (type=user_correction) so semantic similarity search
can retrieve relevant corrections.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Optional

from database.db import database
from memory.ultra_lightweight_memory import store_memory, ultra_lightweight_memory_manager

logger = logging.getLogger(__name__)

corrections_collection = database["user_corrections"]

# Ensure indexes (idempotent)
try:
    corrections_collection.create_index([("user_id", 1), ("created_at", -1)])
    corrections_collection.create_index("hash", unique=True)
    corrections_collection.create_index([("tags", 1)])
except Exception as e:
    logger.debug(f"Index creation skipped for user_corrections: {e}")


def _sanitize(text: str) -> str:
    if not text:
        return text
    # Basic sanitization against prompt injection style control tokens
    forbidden = ["<|", "SYSTEM:", "###", "```system"]
    out = text.strip()
    for token in forbidden:
        out = out.replace(token, " ")
    return out[:2000]  # hard cap


def _make_hash(original_question: str, correction_text: str, user_id: str) -> str:
    base = (original_question or "") + "||" + (correction_text or "") + "||" + user_id
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def remember_correction(
    user_id: str,
    original_question: str,
    original_answer: str,
    correction_text: str,
    tags: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Store a user correction if not duplicate; push to vector store.

    Returns dict with status and id/hash.
    """
    try:
        original_question = _sanitize(original_question)
        original_answer = _sanitize(original_answer)
        correction_text = _sanitize(correction_text)
        h = _make_hash(original_question, correction_text, user_id)

        existing = corrections_collection.find_one({"hash": h})
        if existing:
            return {"status": "duplicate", "hash": h, "_id": str(existing["_id"]) }

        doc = {
            "user_id": user_id,
            "original_question": original_question,
            "original_answer": original_answer,
            "correction_text": correction_text,
            "tags": tags or [],
            "hash": h,
            "created_at": datetime.utcnow(),
            "last_used_at": None,
            "usage_count": 0,
        }
        inserted = corrections_collection.insert_one(doc)

        # Vector store (best-effort)
        try:
            meta = {
                "user": user_id,
                "type": "user_correction",
                "category": "correction",
                "hash": h,
            }
            store_memory(correction_text, meta, importance=0.95)
        except Exception as ve:
            logger.debug(f"Vector insertion for correction failed: {ve}")

        return {"status": "stored", "hash": h, "_id": str(inserted.inserted_id)}
    except Exception as e:
        logger.error(f"Failed to store correction: {e}")
        return {"status": "error", "error": str(e)}


def forget_correction(user_id: str, hash_or_text: str) -> Dict[str, str]:
    """Remove a correction by hash or exact correction_text."""
    try:
        query = {"user_id": user_id, "$or": [{"hash": hash_or_text}, {"correction_text": hash_or_text}]}
        doc = corrections_collection.find_one(query)
        if not doc:
            return {"status": "not_found"}
        corrections_collection.delete_one({"_id": doc["_id"]})
        # Attempt vector deletion (ignore errors) - cannot map reliably without stored id
        return {"status": "deleted", "hash": doc.get("hash")}
    except Exception as e:
        logger.error(f"Failed to forget correction: {e}")
        return {"status": "error", "error": str(e)}


def retrieve_relevant_corrections(
    user_id: str, query: str, top_k: int = 3, min_score: float = 0.65
) -> List[Dict[str, str]]:
    """Retrieve relevant corrections via vector similarity (filter type=user_correction).

    Falls back to regex search if vector query fails.
    """
    results: List[Dict[str, str]] = []
    try:
        # Build embedding for query
        embedding = ultra_lightweight_memory_manager.get_embedding(query)
        # Query underlying pinecone index directly with filter
        index = ultra_lightweight_memory_manager.index
        pine_res = index.query(
            vector=embedding,
            top_k=top_k * 2,  # fetch extra then filter
            include_metadata=True,
            filter={"user": user_id, "type": "user_correction"},
        )
        for m in pine_res.matches:
            score = float(m.score)
            if score < min_score:
                continue
            meta = m.metadata or {}
            hash_val = meta.get("hash")
            corr_doc = corrections_collection.find_one({"hash": hash_val}) if hash_val else None
            if not corr_doc:
                continue
            results.append(
                {
                    "correction_text": corr_doc.get("correction_text"),
                    "original_question": corr_doc.get("original_question"),
                    "hash": corr_doc.get("hash"),
                    "score": score,
                }
            )
    except Exception as e:
        logger.debug(f"Vector correction retrieval failed, fallback to text search: {e}")

    # Fallback if empty
    if not results:
        try:
            import re
            token = query.strip().split(" ")[0]
            # Escape special regex chars to avoid invalid patterns like 2+2
            token = re.escape(token)
            regex = {"$regex": token, "$options": "i"}
            for doc in corrections_collection.find(
                {"user_id": user_id, "$or": [
                    {"correction_text": regex},
                    {"original_question": regex},
                ]}
            ).limit(top_k):
                results.append(
                    {
                        "correction_text": doc.get("correction_text"),
                        "original_question": doc.get("original_question"),
                        "hash": doc.get("hash"),
                        "score": 0.5,
                    }
                )
        except Exception:
            pass

    # Update usage stats
    for r in results:
        try:
            corrections_collection.update_one(
                {"hash": r["hash"]},
                {"$inc": {"usage_count": 1}, "$set": {"last_used_at": datetime.utcnow()}},
            )
        except Exception:
            pass

    return results[:top_k]


def detect_correction_intent(user_message: str) -> bool:
    if not user_message:
        return False
    lowered = user_message.lower()
    triggers = ["actually", "correction:", "it's", "it is", "remember this", "update:"]
    return any(t in lowered for t in triggers)


def detect_forget_intent(user_message: str) -> Optional[str]:
    if not user_message:
        return None
    lowered = user_message.lower()
    # Pattern: "forget this" or "forget <something>"
    if "forget this" in lowered:
        return "THIS"
    if lowered.startswith("forget "):
        return user_message[7:50]
    return None
