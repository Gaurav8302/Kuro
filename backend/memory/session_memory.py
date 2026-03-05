"""Session Memory Manager — Layer 1 (Active Session).

Minimal, deterministic session memory. Fetches the last N raw message
exchanges from MongoDB for the current session. No summarization,
no fact extraction, no hashing, no importance scoring.

Design philosophy:
  Stability > Compression
  Determinism > Heuristics
  Clarity > Cleverness
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from memory.chat_database import chat_db

logger = logging.getLogger(__name__)

# Default number of exchanges (user+assistant pairs) to keep in context.
DEFAULT_EXCHANGE_LIMIT = 15


class SessionMemoryManager:
    """Manages active-session memory using raw MongoDB messages.

    Public API:
        get_recent_messages(session_id, limit) -> List[dict]
        save_message(user_id, message, reply, session_id) -> str
        get_message_count(session_id) -> int
    """

    def __init__(self, exchange_limit: int = DEFAULT_EXCHANGE_LIMIT):
        self.exchange_limit = exchange_limit

    # ------------------------------------------------------------------
    # Read: fetch raw recent exchanges
    # ------------------------------------------------------------------
    def get_recent_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch the last *limit* message exchanges for *session_id*.

        Returns a list of dicts sorted ascending by timestamp:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

        Each MongoDB document stores one exchange (user message + assistant reply).
        We return them as separate role-tagged entries so the LLM sees a proper
        chat-history format.
        """
        limit = limit or self.exchange_limit
        try:
            # Fetch from MongoDB, newest first, then reverse for chronological order
            raw_docs = list(
                chat_db.chat_collection.find(
                    {"session_id": session_id}
                )
                .sort("metadata.sequence_number", -1)
                .limit(limit)
            )
            # Reverse to chronological (oldest first)
            raw_docs.reverse()

            messages: List[Dict[str, Any]] = []
            for doc in raw_docs:
                user_msg = doc.get("message", "")
                assistant_msg = doc.get("reply", "")
                if user_msg:
                    messages.append({"role": "user", "content": user_msg})
                if assistant_msg:
                    messages.append({"role": "assistant", "content": assistant_msg})

            logger.debug(
                "SessionMemory: fetched %d exchanges (%d messages) for session %s",
                len(raw_docs),
                len(messages),
                session_id,
            )
            return messages

        except Exception as e:
            logger.error("SessionMemory: failed to fetch messages for %s: %s", session_id, e)
            return []

    # ------------------------------------------------------------------
    # Write: save a new exchange
    # ------------------------------------------------------------------
    def save_message(
        self,
        user_id: str,
        message: str,
        reply: str,
        session_id: str,
    ) -> str:
        """Persist one exchange to MongoDB via ChatDatabase.

        Returns the session_id (may be generated if not provided).
        """
        try:
            return chat_db.save_chat_to_db(user_id, message, reply, session_id)
        except Exception as e:
            logger.error("SessionMemory: failed to save message: %s", e)
            raise

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------
    def get_message_count(self, session_id: str) -> int:
        """Return total number of exchanges stored for a session."""
        try:
            return chat_db.chat_collection.count_documents({"session_id": session_id})
        except Exception as e:
            logger.error("SessionMemory: count failed for %s: %s", session_id, e)
            return 0


# Global singleton
session_memory = SessionMemoryManager()

__all__ = ["SessionMemoryManager", "session_memory"]
