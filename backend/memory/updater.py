from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json
import logging

# Import the new provenance system
from memory.provenance import (
    MemoryRecord, MemoryProvenance, MemoryType, MemorySource, MemoryStatus,
    MemoryValidator, MemoryConflictResolver
)

# Keep existing imports for backward compatibility
from db.mongo import insert_memory, find_similar_memory_semantic, update_memory, reinforce_memories
from db.pinecone import upsert_vector

logger = logging.getLogger(__name__)


class MemoryUpdater:
    def __init__(self):
        # Lazy load LLM to avoid circular imports
        self._llm = None
    
    @property
    def llm(self):
        if self._llm is None:
            from llm.router import LLMRouter
            self._llm = LLMRouter().get_model("mid")
        return self._llm

    async def process(self, user_id, user_input, assistant_response):
        """Process a conversation turn and extract memories with provenance in a single batch."""
        extracted_items = await self.extract_memory_batch(user_input, assistant_response)

        type_map = {
            "fact": MemoryType.FACT,
            "preference": MemoryType.PREFERENCE,
            "event": MemoryType.EVENT,
            "facts": MemoryType.FACT,
            "preferences": MemoryType.PREFERENCE,
            "events": MemoryType.EVENT,
        }

        for item in extracted_items:
            content = (item.get("content") or "").strip()
            if not content:
                continue

            raw_type = str(item.get("type", "fact")).lower().strip()
            normalized_type = type_map.get(raw_type, MemoryType.FACT)

            try:
                importance = float(item.get("importance", 5.0))
            except (ValueError, TypeError):
                importance = 5.0

            # Create memory record with full provenance
            memory = MemoryRecord(
                user_id=user_id,
                memory_type=normalized_type,
                content=content,
                importance=importance,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                provenance=MemoryProvenance(
                    source=MemorySource.EXTRACTED_BY_LLM,
                    extraction_model="mid",
                    extraction_timestamp=datetime.now(timezone.utc),
                    confidence=0.8,
                    tags=["auto_extracted"]
                ),
                embedding_model="gemini-embedding-001",
            )

            # Validate before storing
            errors = MemoryValidator.validate(memory)
            if errors:
                logger.warning("Memory validation failed for user %s: %s", user_id, errors)
                continue

            # Sanitize to remove any potential sensitive data
            memory = MemoryValidator.sanitize(memory)

            try:
                await self._upsert(memory)
            except Exception as e:
                logger.error("Failed to upsert extracted memory for user %s: %s", user_id, e)

    async def extract_memory_batch(self, user_input: str, response: str) -> List[Dict[str, Any]]:
        """Extract memory items in a single consolidated LLM call."""
        words = (user_input or "").strip().split()
        if len(words) <= 2 and any(w.lower() in {"hi", "hello", "hey", "thanks", "ok", "bye", "cool"} for w in words):
            return []

        prompt = f"""Extract notable long-term facts, user preferences, personal details, or ongoing projects from this conversation.
Only extract lasting facts worth remembering across future sessions. Do NOT extract transient conversation or generic banter.

Return a JSON list:
[
  {{
    "type": "fact",  // "fact" | "preference" | "event"
    "content": "...",
    "importance": 7.0  // 1-10 scale
  }}
]

If there are no lasting facts or preferences to extract, return: []

Conversation:
User: {user_input}
Assistant: {response}"""

        try:
            result = await self.llm.generate(prompt)
            text = (result or "").strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # Fallback if model returned dictionary with keys
                items = []
                for k, vals in parsed.items():
                    k_norm = "preference" if "pref" in k else ("event" if "event" in k else "fact")
                    if isinstance(vals, list):
                        for v in vals:
                            if isinstance(v, str) and v.strip():
                                items.append({"content": v.strip(), "type": k_norm, "importance": 6.0})
                            elif isinstance(v, dict) and v.get("content"):
                                items.append(v)
                return items
            return []
        except Exception as e:
            logger.warning("Failed to extract memory batch: %s", e)
            return []

    async def extract_memory(self, user_input, response):
        """Backward-compatible extraction helper."""
        batch = await self.extract_memory_batch(user_input, response)
        out = {"facts": [], "preferences": [], "events": []}
        for item in batch:
            t = item.get("type", "fact").lower()
            c = item.get("content", "")
            if "pref" in t:
                out["preferences"].append(c)
            elif "event" in t:
                out["events"].append(c)
            else:
                out["facts"].append(c)
        return out

    async def score_importance(self, content):
        """Backward-compatible importance scorer."""
        return 5.0

    async def resolve_conflict(self, old_content, new_content):
        if old_content.strip().lower() == new_content.strip().lower():
            return old_content

        prompt = f"""Resolve conflict between these two related memories. Keep the most up-to-date and accurate information. Combine them if they are both valid but slightly different aspects.

Old: {old_content}
New: {new_content}

Return ONLY the best unified version of the memory."""

        try:
            return await self.llm.generate(prompt)
        except Exception:
            return new_content

    async def _upsert(self, memory: 'MemoryRecord'):
        """Upsert memory with conflict resolution and provenance tracking."""
        # Find similar existing memory
        existing = find_similar_memory_semantic(
            content=memory.content,
            user_id=memory.user_id,
            memory_types=[memory.memory_type.value],
            min_score=0.85,
        )

        if existing:
            # Create MemoryRecord from existing data
            existing_record = MemoryRecord(
                memory_id=str(existing.get("_id")),
                user_id=memory.user_id,
                memory_type=MemoryType(existing.get("type", "fact")),
                content=existing.get("content", ""),
                importance=float(existing.get("importance", 0.5)),
                created_at=existing.get("created_at", datetime.now(timezone.utc)),
                updated_at=existing.get("updated_at", datetime.now(timezone.utc)),
                status=MemoryStatus(existing.get("status", "active")),
                provenance=MemoryProvenance(
                    source=MemorySource(existing.get("provenance", {}).get("source", "extracted_by_llm")),
                    confidence=existing.get("provenance", {}).get("confidence", 0.5),
                    user_confirmed=existing.get("provenance", {}).get("user_confirmed", False),
                ),
                version=existing.get("version", 1),
            )

            # Resolve conflict using provenance-aware resolver
            merged = MemoryConflictResolver.resolve(
                existing_record, memory, 
                strategy="user_confirmed_wins"  # Prefer user-confirmed memories
            )

            # Update merged record
            merged.content = await self.resolve_conflict(existing_record.content, memory.content)
            
            # Calculate importance with decay
            days_old = (datetime.now(timezone.utc) - existing_record.created_at).days
            existing_decayed_importance = float(existing_record.importance) * (0.97 ** max(days_old, 0))
            merged.importance = max(existing_decayed_importance, memory.importance) + 0.5
            
            # Track provenance
            merged.provenance.tags = existing_record.provenance.tags + ["merged", "conflict_resolved"]
            merged.provenance.supersedes = existing_record.memory_id
            merged.previous_version_id = existing_record.memory_id
            merged.version = existing_record.version + 1

            # Update in database
            update_memory(
                existing["_id"], 
                {
                    "content": merged.content,
                    "importance": merged.importance,
                    "updated_at": datetime.now(timezone.utc),
                    "provenance": merged.provenance.__dict__,
                    "version": merged.version,
                    "previous_version_id": merged.previous_version_id,
                }, 
                memory.user_id
            )
            
            # Update Pinecone
            upsert_vector(
                vec_id=str(existing["_id"]),
                text=merged.content,
                user_id=memory.user_id,
                memory_type=merged.memory_type.value,
                importance=merged.importance
            )
        else:
            # Insert new memory
            memory_dict = memory.to_dict()
            # Remove fields that shouldn't be in MongoDB
            mongo_doc = {k: v for k, v in memory_dict.items() 
                        if k not in ["provenance", "status", "version", "previous_version_id", "embedding_id"]}
            mongo_doc["provenance"] = memory.provenance.__dict__
            mongo_doc["status"] = memory.status.value
            mongo_doc["version"] = memory.version
            mongo_doc["type"] = memory.memory_type.value
            mongo_doc["memory_type"] = memory.memory_type.value
            
            inserted_id = insert_memory(mongo_doc)
            memory.memory_id = str(inserted_id)
            memory.embedding_id = str(inserted_id)
            
            logger.info(f"Inserted new memory {inserted_id} for user {memory.user_id}")

    def reinforce_memories(self, memories, user_id):
        memory_ids = []
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            memory_id = memory.get("metadata", {}).get("id")
            if memory_id:
                memory_ids.append(memory_id)
        if memory_ids:
            reinforce_memories(memory_ids, user_id)