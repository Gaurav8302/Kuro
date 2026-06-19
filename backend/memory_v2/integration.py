"""Integration adapter — wires Reflection Engine into the existing Kuro backend.

Connects memory_v2's ReflectionEngine to chatbot.py, chat_manager_v3.py,
and the existing memory pipeline via dependency injection and event hooks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from memory_v2 import DEFAULT_REFLECTION_CONFIG, ReflectionConfig, ReflectionEngine

logger = logging.getLogger(__name__)


class ReflectionIntegration:
    """Thin facade that wires ReflectionEngine into the live system.

    Designed to be created once in chatbot.py and passed as a dependency
    to ChatManagerV3 and MemoryUpdater. All failures are caught and logged
    so that reflection never blocks or corrupts the main chat flow.
    """

    def __init__(
        self,
        engine: Optional[ReflectionEngine] = None,
        config: Optional[ReflectionConfig] = None,
    ):
        self.config = config or DEFAULT_REFLECTION_CONFIG
        self.engine = engine or ReflectionEngine(config=self.config)
        self._background_task: Optional[asyncio.Task] = None

    # ── Context augmentation ──────────────────────────────────────────

    async def augment_context(
        self,
        user_id: str,
        query: str,
        existing_memories: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Retrieve relevant insights and return as context entries.

        Returns a list of dicts with ``role`` and ``content`` keys suitable
        for injecting into the system prompt. Returns empty list when the
        query is not meta-cognitive or no insights match.
        """
        try:
            insights = self.engine.retrieve_relevant_insights(user_id, query)
            if not insights:
                return []
            return [
                {
                    "role": "system",
                    "content": (
                        f"[Insight] {i.insight_text} "
                        f"(confidence: {i.confidence:.2f})"
                    ),
                }
                for i in insights
            ]
        except Exception:
            logger.exception("ReflectionIntegration.augment_context failed")
            return []

    # ── Memory lifecycle hooks ────────────────────────────────────────

    async def on_memories_processed(self, user_id: str, count: int) -> None:
        """Called after new memories are extracted and stored."""
        try:
            self.engine.scheduler.on_memories_added(user_id, count)
            if self.engine.scheduler.should_reflect(user_id, "memory_threshold"):
                await self.engine.reflect_on_new_memory(user_id)
        except Exception:
            logger.exception("ReflectionIntegration.on_memories_processed failed")

    async def on_session_end(self, user_id: str) -> None:
        """Called when a session ends (before creating a new one)."""
        try:
            await self.engine.reflect_on_session_end(user_id)
        except Exception:
            logger.exception("ReflectionIntegration.on_session_end failed")

    # ── Correction handling ──────────────────────────────────────────

    async def handle_correction(self, user_id: str, message: str) -> bool:
        """Detect and handle user corrections. Returns True if correction was processed."""
        try:
            archived = self.engine.handle_correction(user_id, message)
            return len(archived) > 0
        except Exception:
            logger.exception("ReflectionIntegration.handle_correction failed")
            return False

    # ── Background scheduler ─────────────────────────────────────────

    def start_background(self) -> None:
        """Start the background reflection scheduler (sync, creates own task)."""
        if self._background_task is None or self._background_task.done():
            self.engine.scheduler.start_background()
            self._background_task = self.engine.scheduler._background_task
            logger.info("Background reflection scheduler started")

    async def stop_background(self) -> None:
        """Stop the background scheduler task."""
        if self._background_task and not self._background_task.done():
            await self.engine.scheduler.stop_background()
            self._background_task = None
            logger.info("Background reflection scheduler stopped")

    # ── Factory helpers ──────────────────────────────────────────────

    @staticmethod
    def make_memory_loader(chat_db, session_memory, long_term_memory):
        """Create a memory_loader_fn for the ReflectionEngine.

        Returns an async callable that gathers memories from MongoDB and Pinecone.
        """
        async def loader(user_id: str) -> List[Dict[str, Any]]:
            memories: List[Dict[str, Any]] = []
            try:
                sessions = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: chat_db.get_sessions_by_user(user_id)
                )
                for session in (sessions or [])[:5]:
                    sid = session.get("session_id")
                    if not sid:
                        continue
                    messages = session_memory.get_recent_messages(
                        sid, limit=10
                    ) or []
                    for msg in messages:
                        content = msg.get("content", "")
                        role = msg.get("role", "user")
                        memories.append({
                            "content": content,
                            "type": role,
                            "session_id": sid,
                            "timestamp": msg.get("timestamp", ""),
                        })
            except Exception:
                logger.exception("memory_loader failed")
            return memories

        return loader

    @staticmethod
    def make_llm_fn(llm_router):
        """Create an llm_fn for the ReflectionEngine.

        Returns an async callable ``(prompt: str) -> str`` using the
        existing LLMRouter infrastructure.
        """
        async def llm_wrapper(prompt: str) -> str:
            model = llm_router.get_model("mid")
            return await model.generate(prompt)

        return llm_wrapper
