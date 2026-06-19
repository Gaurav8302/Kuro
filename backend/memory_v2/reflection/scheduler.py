"""Reflection scheduler — triggers reflection on configurable events.

Follows MEMORY_REFLECTION.md Section 1 (When Reflection Runs).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from memory_v2.reflection.config import DEFAULT_REFLECTION_CONFIG, ReflectionConfig

logger = logging.getLogger(__name__)


class ReflectionScheduler:
    """Manages when reflection analysis runs.

    Triggers:
      - After N new memories have been added (threshold-based)
      - After a configurable time interval has elapsed
      - On session end (optional)
      - On-demand (explicit call)
    """

    def __init__(
        self,
        reflection_fn: Optional[Callable] = None,
        config: Optional[ReflectionConfig] = None,
    ):
        self.config = config or DEFAULT_REFLECTION_CONFIG
        self._reflection_fn = reflection_fn
        self._memory_count_since_last_reflection: int = 0
        self._last_reflection_time: float = 0.0
        self._background_task: Optional[asyncio.Task] = None
        self._running = False

    def set_reflection_fn(self, fn: Callable) -> None:
        self._reflection_fn = fn

    def record_memory_added(self, count: int = 1) -> bool:
        """Record that new memories have been added.

        Returns True if reflection should run.
        """
        self._memory_count_since_last_reflection += count
        if (
            self._memory_count_since_last_reflection
            >= self.config.reflection_after_n_memories
        ):
            logger.info(
                "Reflection threshold reached: %d new memories (threshold=%d)",
                self._memory_count_since_last_reflection,
                self.config.reflection_after_n_memories,
            )
            return True
        return False

    def time_interval_elapsed(self) -> bool:
        """Check if the periodic time interval has passed."""
        if self._last_reflection_time == 0.0:
            self._last_reflection_time = time.time()
            return False
        elapsed = time.time() - self._last_reflection_time
        interval_seconds = self.config.reflection_interval_minutes * 60
        return elapsed >= interval_seconds

    async def maybe_reflect(self, user_id: str, **context) -> bool:
        """Check triggers and run reflection if any trigger fires.

        Returns True if reflection was executed.
        """
        if not self._reflection_fn:
            logger.warning("No reflection function set; cannot reflect.")
            return False

        should_reflect = False
        reason = ""

        if self.record_memory_added(0):  # Check without incrementing
            should_reflect = True
            reason = "memory_threshold"

        if self.time_interval_elapsed():
            should_reflect = True
            reason = "time_interval"

        if context.get("force"):
            should_reflect = True
            reason = "on_demand"

        if context.get("session_end") and self.config.reflection_on_session_end:
            should_reflect = True
            reason = "session_end"

        if not should_reflect:
            return False

        logger.info("Reflection triggered by: %s (user=%s)", reason, user_id)
        try:
            if asyncio.iscoroutinefunction(self._reflection_fn):
                await self._reflection_fn(user_id=user_id, reason=reason)
            else:
                self._reflection_fn(user_id=user_id, reason=reason)
        except Exception as e:
            logger.error("Reflection failed for user %s: %s", user_id, e)
            return False

        self._memory_count_since_last_reflection = 0
        self._last_reflection_time = time.time()
        return True

    async def reflect_on_demand(self, user_id: str) -> bool:
        """Force an immediate reflection run."""
        return await self.maybe_reflect(user_id, force=True)

    async def reflect_on_session_end(self, user_id: str) -> bool:
        """Run reflection at session end."""
        if not self.config.reflection_on_session_end:
            return False
        return await self.maybe_reflect(user_id, session_end=True)

    def start_background(self, interval_seconds: int = 3600) -> None:
        """Start a background loop that checks time-based reflection."""
        if self._running:
            return
        self._running = True
        self._background_task = asyncio.create_task(self._background_loop(interval_seconds))
        logger.info("Reflection background scheduler started (interval=%ds)", interval_seconds)

    async def stop_background(self) -> None:
        """Stop the background scheduler loop."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        logger.info("Reflection background scheduler stopped")

    async def _background_loop(self, interval_seconds: int) -> None:
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
