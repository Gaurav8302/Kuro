"""
Memory Updater — Batched Extraction with Rule-Based Importance

Extracts memorable facts, preferences, and events from conversations
and stores them in the memory system. Key optimization: instead of
making 2 LLM calls per turn (extract + score), this version batches
turns and makes 1 LLM call per batch (default: every 5 turns).

Previous version: 2 LLM calls × every turn = ~1000ms per turn
New version:      1 LLM call × every 5 turns = ~100ms amortized per turn

Importance scoring is now rule-based (no LLM call).
"""

import asyncio
import logging
import re
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from db.mongo import insert_memory, find_similar_memory_semantic, update_memory, reinforce_memories

logger = logging.getLogger(__name__)


class MemoryUpdater:
    """Batched memory extraction with rule-based importance scoring."""

    # Number of conversation turns to batch before extraction
    # Tuneable via env for faster memory capture (default 3)
    BATCH_SIZE = int(os.getenv("MEMORY_BATCH_SIZE", "3"))

    def __init__(self):
        from llm.router import LLMRouter
        self.llm = LLMRouter().get_model("mid")
        # Per-user turn buffers: {user_id: [(user_msg, assistant_msg), ...]}
        self._buffers: Dict[str, List[Tuple[str, str]]] = {}
        self._buffer_timestamps: Dict[str, datetime] = {}
        self._buffer_ttl_seconds = 300  # 5 min TTL to prevent stale buffer leaks
        self._lock = asyncio.Lock()

    async def process(self, user_id: str, user_input: str, assistant_response: str):
        """Buffer a turn and extract when batch is full or buffer is stale."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            if user_id not in self._buffers:
                self._buffers[user_id] = []
                self._buffer_timestamps[user_id] = now
            self._buffers[user_id].append((user_input, assistant_response))
            self._buffer_timestamps[user_id] = now

            buf_len = len(self._buffers[user_id])
            if buf_len >= self.BATCH_SIZE:
                batch = self._buffers.pop(user_id)
                self._buffer_timestamps.pop(user_id, None)
            elif (now - self._buffer_timestamps[user_id]).total_seconds() > self._buffer_ttl_seconds:
                # TTL expired — flush partial buffer to prevent memory leak
                batch = self._buffers.pop(user_id)
                self._buffer_timestamps.pop(user_id, None)
            else:
                return  # Not enough turns yet

        # Process outside the lock
        await self._process_batch(user_id, batch)

    async def flush(self, user_id: str):
        """Force-flush any buffered turns for a user (e.g. on session end)."""
        async with self._lock:
            batch = self._buffers.pop(user_id, [])
        if batch:
            await self._process_batch(user_id, batch)

    async def _process_batch(
        self, user_id: str, batch: List[Tuple[str, str]]
    ):
        """Extract memories from a batch of turns with a single LLM call."""
        if not batch:
            return

        extracted = await self._extract_memories_batch(batch)

        type_map = {
            "facts": "fact", "preferences": "preference", "events": "event",
            "fact": "fact", "preference": "preference", "event": "event",
        }

        for mem_type, items in extracted.items():
            normalized_type = type_map.get(str(mem_type).lower())
            if not normalized_type:
                continue
            for content in items:
                if not isinstance(content, str) or not content.strip():
                    continue
                # Rule-based importance scoring — no LLM call
                importance = self._score_importance_rule(content, normalized_type)

                memory = {
                    "user_id": user_id,
                    "type": normalized_type,
                    "content": content.strip(),
                    "importance": importance,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }

                try:
                    await self._upsert(memory)
                except Exception as e:
                    logger.error("Failed to upsert memory: %s", e)

    async def _extract_memories_batch(
        self, batch: List[Tuple[str, str]]
    ) -> Dict[str, List[str]]:
        """Single LLM call to extract memories from multiple turns."""
        transcript = "\n".join(
            f"User: {u}\nAssistant: {a}" for u, a in batch
        )

        prompt = f"""Extract memorable information from this conversation.
Only extract concrete, specific facts about the user that will remain true long-term.
Skip temporary plans, short-lived tasks, transient states, or anything likely to change soon.
Skip greetings, filler, and anything not worth remembering.

Return strict JSON only (no markdown, no commentary):
{
    "facts": ["specific factual info about the user"],
    "preferences": ["user likes/dislikes/preferences"],
    "events": ["specific events or experiences mentioned"]
}

Rules:
- Keep each item short (1 sentence max)
- De-duplicate semantically similar items
- If nothing is worth remembering, return empty arrays

Conversation ({len(batch)} turns):
{transcript}
"""

        try:
            result = await self.llm.generate(prompt)
            return self._parse_extraction(result)
        except Exception as e:
            logger.error("Memory extraction failed: %s", e)
            return {"facts": [], "preferences": [], "events": []}

    @staticmethod
    def _score_importance_rule(content: str, memory_type: str) -> float:
        """Rule-based importance scoring — no LLM call needed."""
        score = 5.0  # Base

        # Type-based base adjustment
        type_bonus = {"preference": 1.0, "fact": 0.5, "event": 0.0}
        score += type_bonus.get(memory_type, 0.0)

        content_lower = content.lower()
        words = content.split()
        word_count = len(words)

        # Specificity bonus: contains names, numbers, dates
        if re.search(r"\b[A-Z][a-z]+\b", content):  # Proper nouns
            score += 1.0
        if re.search(r"\b\d+\b", content):  # Numbers
            score += 0.5
        if re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|\d{4})\b", content_lower):
            score += 0.5  # Dates

        # Length bonus: more detailed = more important (up to a point)
        if word_count >= 10:
            score += 0.5
        elif word_count < 4:
            score -= 1.0  # Too vague

        # High-value content markers
        high_value_markers = {"name is", "birthday", "work at", "live in", "email", "phone", "study"}
        if any(m in content_lower for m in high_value_markers):
            score += 1.5

        # Low-value content markers
        low_value_markers = {"maybe", "i think", "not sure", "probably", "idk"}
        if any(m in content_lower for m in low_value_markers):
            score -= 1.0

        return max(1.0, min(10.0, score))

    async def _upsert(self, new_memory: Dict[str, Any]):
        """Upsert memory with conflict resolution."""
        loop = asyncio.get_running_loop()
        existing = await loop.run_in_executor(None, lambda: find_similar_memory_semantic(
            content=new_memory["content"],
            user_id=new_memory["user_id"],
            memory_types=[new_memory["type"]],
            min_score=0.85,
        ))

        if existing:
            # Merge: keep the newer, more detailed version
            merged_content = self._merge_memories(
                existing.get("content", ""), new_memory["content"]
            )

            existing_updated = existing.get("updated_at") or existing.get("created_at") or datetime.now(timezone.utc)
            if isinstance(existing_updated, str):
                try:
                    existing_updated = datetime.fromisoformat(existing_updated.replace("Z", "+00:00"))
                except Exception:
                    existing_updated = datetime.now(timezone.utc)

            days_old = max(0, (datetime.now(timezone.utc) - existing_updated).days)
            existing_decayed = float(existing.get("importance", 5.0)) * (0.97 ** days_old)

            new_importance = max(existing_decayed, new_memory["importance"]) + 1

            await loop.run_in_executor(None, lambda: update_memory(existing["_id"], {
                "content": merged_content,
                "importance": min(new_importance, 10.0),
                "updated_at": datetime.now(timezone.utc),
            }))
        else:
            await loop.run_in_executor(None, lambda: insert_memory(new_memory))

    @staticmethod
    def _merge_memories(old_content: str, new_content: str) -> str:
        """Rule-based memory merge — keep the longer, more specific version.
        No LLM call needed for this.
        """
        old_words = len(old_content.split())
        new_words = len(new_content.split())

        # If new content is significantly more detailed, prefer it
        if new_words > old_words * 1.5:
            return new_content

        # If old is more detailed, keep old but note the update
        if old_words > new_words * 1.5:
            return old_content

        # Similar length: prefer the newer one (more up-to-date)
        return new_content

    def reinforce_memories(self, memories: List[Dict[str, Any]]):
        """Reinforce retrieved memories by incrementing their importance."""
        memory_ids = []
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            memory_id = memory.get("metadata", {}).get("id")
            if memory_id:
                memory_ids.append(memory_id)
        if memory_ids:
            reinforce_memories(memory_ids)

    @staticmethod
    def _parse_extraction(result: str) -> Dict[str, List[str]]:
        """Parse LLM extraction result into structured dict."""
        try:
            text = (result or "").strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"facts": [], "preferences": [], "events": []}
