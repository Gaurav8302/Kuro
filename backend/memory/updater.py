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
        """Process a conversation turn and extract memories with provenance."""
        extracted = await self.extract_memory(user_input, assistant_response)

        type_map = {
            "facts": MemoryType.FACT,
            "preferences": MemoryType.PREFERENCE,
            "events": MemoryType.EVENT,
            "fact": MemoryType.FACT,
            "preference": MemoryType.PREFERENCE,
            "event": MemoryType.EVENT,
        }

        for mem_type_str, items in extracted.items():
            normalized_type = type_map.get(str(mem_type_str).lower())
            if not normalized_type:
                continue
            for content in items:
                if not isinstance(content, str) or not content.strip():
                    continue
                importance = await self.score_importance(content)

                # Create memory record with full provenance
                memory = MemoryRecord(
                    user_id=user_id,
                    memory_type=normalized_type,
                    content=content.strip(),
                    importance=importance,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    provenance=MemoryProvenance(
                        source=MemorySource.EXTRACTED_BY_LLM,
                        extraction_model="mid",  # or actual model name
                        extraction_timestamp=datetime.now(timezone.utc),
                        confidence=0.7,  # Default confidence for LLM extraction
                        tags=["auto_extracted"]
                    ),
                    embedding_model="gemini-embedding-001",
                )

                # Validate before storing
                errors = MemoryValidator.validate(memory)
                if errors:
                    logger.warning(f"Memory validation failed for user {user_id}: {errors}")
                    continue

                # Sanitize to remove any potential sensitive data
                memory = MemoryValidator.sanitize(memory)

                await self._upsert(memory)

    async def extract_memory(self, user_input, response):
        """Extract memory from conversation using LLM."""
        prompt = f"""Extract memory from the following conversation.

Return JSON:
{{
    "facts": ["..."],
    "preferences": ["..."],
    "events": ["..."]
}}

Conversation:
User: {user_input}
Assistant: {response}"""

        result = await self.llm.generate(prompt)

        try:
            text = result.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            logger.warning(f"Failed to parse memory extraction: {e}")
            return {"facts": [], "preferences": [], "events": []}

    async def score_importance(self, content):
        prompt = f"""Rate importance (1-10) of the following memory fact:
"{content}"
Return ONLY the integer."""

        result = await self.llm.generate(prompt)

        try:
            return float(result.strip())
        except:
            return 5.0

    async def resolve_conflict(self, old_content, new_content):
        prompt = f"""Resolve conflict between these two related memories. Keep the most up-to-date and accurate information. Combine them if they are both valid but slightly different aspects.

Old: {old_content}
New: {new_content}

Return ONLY the best unified version of the memory."""

        return await self.llm.generate(prompt)

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