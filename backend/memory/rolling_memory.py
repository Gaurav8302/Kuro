"""Rolling Memory & Progressive Summarization System.

Maintains a short-term detailed window and long-term summarized memory.

Key features:
 - Short-term window of last N exchanges (full fidelity).
 - Older exchanges summarized into structured, information-rich chunks.
 - Content hashing prevents re-summarizing unchanged segments.
 - Summaries stored in MongoDB (conversation_summaries) and vector store (Pinecone) using existing store_memory utility.
 - Pluggable summarizer (dependency injection) for different LLM providers.
 - Non-blocking summarization via background thread (fast return path).
"""

from __future__ import annotations

import threading
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Optional, Protocol, Any

from database.db import database
from memory.chat_database import chat_db
from memory.summarization_prompts import build_summarization_prompt
from memory.layered_summarization_prompts import build_layered_prompt
from memory.ultra_lightweight_memory import store_memory

logger = logging.getLogger(__name__)

# Mongo collection for conversation summaries
tick = database
conversation_summaries = database["conversation_summaries"]


class Summarizer(Protocol):  # interface
    def summarize(self, prompt: str) -> str: ...


class GroqSummarizer:
    """Default summarizer using GroqClient (synchronous)."""
    def __init__(self):
        try:
            from utils.groq_client import GroqClient
            self.client = GroqClient()
        except Exception as e:
            logger.error(f"Failed to init GroqSummarizer: {e}")
            self.client = None

    def summarize(self, prompt: str) -> str:
        if not self.client:
            return "FACTS:\nOTHER_NOTES:\n- (summarizer unavailable)"
        try:
            return self.client.generate_content(prompt)
        except Exception as e:
            logger.error(f"Groq summarization failed: {e}")
            return "FACTS:\nOTHER_NOTES:\n- (summarization error)"


class RollingMemoryManager:
    def __init__(
        self,
        short_term_window: int = 12,
        min_chunk: int = 6,
        summarization_strategy: str = "balanced",
        summarizer: Optional[Summarizer] = None,
    ):
        self.short_term_window = short_term_window
        self.min_chunk = min_chunk
        self.strategy = summarization_strategy
        self.summarizer = summarizer or GroqSummarizer()
        self._lock = threading.Lock()

        # Indexes (idempotent)
        try:
            conversation_summaries.create_index(
                [("session_id", 1), ("sequence_end", 1)]
            )
            conversation_summaries.create_index(
                [("user_id", 1), ("created_at", -1)]
            )
            conversation_summaries.create_index([("hash", 1)])
        except Exception as e:
            logger.warning(f"Could not ensure indexes for conversation_summaries: {e}")

    # ---------- Public API ----------
    def schedule_summarization(self, user_id: str, session_id: str):
        """Non-blocking summarization trigger."""
        thread = threading.Thread(
            target=self._maybe_summarize_session,
            args=(user_id, session_id),
            daemon=True,
        )
        thread.start()

    def get_short_term_messages(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        messages = chat_db.chat_collection.find(
            {"session_id": session_id}
        ).sort("metadata.sequence_number", -1).limit(self.short_term_window)
        out = []
        for m in messages:
            out.append(
                {
                    "sequence": m.get("metadata", {}).get("sequence_number", 0),
                    "user": m.get("message"),
                    "assistant": m.get("reply"),
                    "timestamp": m.get("timestamp"),
                }
            )
        return list(reversed(out))  # chronological

    def get_relevant_summaries(
        self, user_id: str, session_id: Optional[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        cur = conversation_summaries.find(query).sort("created_at", -1).limit(limit)
        return [
            {
                "summary": c.get("summary"),
                "sequence_start": c.get("sequence_start"),
                "sequence_end": c.get("sequence_end"),
            }
            for c in cur
        ]

    def build_memory_context(
        self, user_id: str, session_id: str, current_message: str, long_term_limit: int = 4
    ) -> Dict[str, Any]:
        short_term = self.get_short_term_messages(session_id)
        summaries = self.get_relevant_summaries(user_id, session_id, long_term_limit)
        # Simple redundancy removal between summaries
        seen_lines = set()
        dedup_summaries: List[str] = []
        for s in summaries:
            lines = [ln.strip() for ln in s["summary"].splitlines() if ln.strip()]
            filtered = []
            for ln in lines:
                key = ln.lower()
                if key in seen_lines:
                    continue
                seen_lines.add(key)
                filtered.append(ln)
            if filtered:
                dedup_summaries.append("\n".join(filtered))
        return {
            "short_term": short_term,
            "long_term_summaries": dedup_summaries,
        }

    # ---------- Internal logic ----------
    def _maybe_summarize_session(self, user_id: str, session_id: str):
        try:
            with self._lock:  # prevent race on same session
                total_messages = chat_db.chat_collection.count_documents(
                    {"session_id": session_id}
                )
                if total_messages <= self.short_term_window + self.min_chunk:
                    return  # Not enough history yet

                # Determine already summarized range
                last_summary = (
                    conversation_summaries.find({"session_id": session_id})
                    .sort("sequence_end", -1)
                    .limit(1)
                )
                last_end = 0
                for ls in last_summary:
                    last_end = ls.get("sequence_end", 0)

                # Determine new range end (exclude short-term window)
                # Each message is one document; sequence numbers are 1-based per chat_database
                target_end = total_messages - self.short_term_window
                if target_end <= last_end + self.min_chunk - 1:
                    return  # Not enough new messages beyond short-term

                # Chunk to summarize = (last_end+1) .. target_end
                to_summarize = list(
                    chat_db.chat_collection.find(
                        {
                            "session_id": session_id,
                            "metadata.sequence_number": {"$gt": last_end, "$lte": target_end},
                        }
                    ).sort("metadata.sequence_number", 1)
                )
                if not to_summarize:
                    return

                block_text_lines = []
                seq_start, seq_end = None, None
                for doc in to_summarize:
                    seq = doc.get("metadata", {}).get("sequence_number", 0)
                    if seq_start is None:
                        seq_start = seq
                    seq_end = seq
                    block_text_lines.append(
                        f"User: {doc.get('message')}\nAssistant: {doc.get('reply')}"
                    )
                block_text = "\n\n".join(block_text_lines)
                content_hash = hashlib.sha256(block_text.encode("utf-8")).hexdigest()

                # Skip if identical hash already stored for same range
                existing = conversation_summaries.find_one(
                    {
                        "session_id": session_id,
                        "sequence_start": seq_start,
                        "sequence_end": seq_end,
                        "hash": content_hash,
                    }
                )
                if existing:
                    logger.debug(
                        f"Skipping summarization for {session_id} {seq_start}-{seq_end} (unchanged)"
                    )
                    return

                # Build two-layer summarizations: legacy + layered
                prompt = build_summarization_prompt(block_text, self.strategy)
                layered_prompt = build_layered_prompt(block_text)
                summary_text = self.summarizer.summarize(prompt)
                layered_summary = self.summarizer.summarize(layered_prompt)

                # Extract high-value verbatim facts (simple heuristic lines starting with '- ' under FACTS or FACTS_COMMITMENTS)
                verbatim_facts: list[str] = []
                for line in layered_summary.splitlines():
                    l = line.strip()
                    if l.startswith('-') and any(h in line.upper() for h in ['FACTS', 'FACTS_COMMITMENTS']):
                        # section headers won't start with '-', only fact lines inside sections
                        verbatim_facts.append(l)

                record = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "sequence_start": seq_start,
                    "sequence_end": seq_end,
                    "summary": summary_text,
                    "layered_summary": layered_summary,
                    "verbatim_facts": verbatim_facts,
                    "raw_block_store": block_text[:8000],  # diagnostic slice
                    "hash": content_hash,
                    "strategy": self.strategy,
                    "created_at": datetime.utcnow(),
                }
                conversation_summaries.insert_one(record)

                # Also store vectorized for semantic recall
                try:
                    meta = {
                        "user": user_id,
                        "type": "long_term_summary",
                        "category": "summary",
                        "session_id": session_id,
                        "sequence_start": seq_start,
                        "sequence_end": seq_end,
                        "strategy": self.strategy,
                    }
                    store_memory(summary_text, meta, importance=0.85)
                    if layered_summary:
                        store_memory(layered_summary, {**meta, "type": "layered_summary"}, importance=0.9)
                        for vf in verbatim_facts[:10]:
                            store_memory(vf, {**meta, "type": "verbatim_fact"}, importance=0.95)
                except Exception as ve:
                    logger.debug(f"Vector store push skipped: {ve}")

                logger.info(
                    f"Summarized session {session_id} seq {seq_start}-{seq_end} into {len(summary_text)} chars"
                )
        except Exception as e:
            logger.error(f"Rolling summarization failed: {e}")


# Global instance
rolling_memory_manager = RollingMemoryManager()
