"""
Execution Guards — Safety Limits for Agent Operations

Provides configurable safety boundaries for any autonomous
or multi-step operations. Prevents runaway loops, excessive
token consumption, and unauthorized destructive actions.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


@dataclass
class GuardConfig:
    """Configuration for execution guards."""
    max_iterations: int = 10
    max_timeout_seconds: int = 120
    max_total_tokens: int = 50000
    max_tool_calls: int = 20
    allow_destructive: bool = False
    require_approval_for: list = field(default_factory=lambda: [
        "file_delete", "shell_exec", "db_write", "network_request",
    ])


class ExecutionGuard:
    """Wraps any autonomous execution with safety limits."""

    def __init__(self, config: Optional[GuardConfig] = None):
        self.config = config or GuardConfig()
        self._iteration_count = 0
        self._token_count = 0
        self._tool_call_count = 0
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """Begin tracking a guarded execution."""
        self._start_time = time.monotonic()
        self._iteration_count = 0
        self._token_count = 0
        self._tool_call_count = 0

    def check_iteration(self) -> bool:
        """Check if another iteration is allowed. Returns False if limit hit."""
        self._iteration_count += 1
        if self._iteration_count > self.config.max_iterations:
            logger.warning(
                "Guard: iteration limit reached (%d/%d)",
                self._iteration_count, self.config.max_iterations,
            )
            return False
        return True

    def check_timeout(self) -> bool:
        """Check if execution is within timeout. Returns False if exceeded."""
        if self._start_time is None:
            return True
        elapsed = time.monotonic() - self._start_time
        if elapsed > self.config.max_timeout_seconds:
            logger.warning(
                "Guard: timeout exceeded (%.1fs/%.1fs)",
                elapsed, self.config.max_timeout_seconds,
            )
            return False
        return True

    def record_tokens(self, count: int) -> bool:
        """Record token usage. Returns False if budget exceeded."""
        self._token_count += count
        if self._token_count > self.config.max_total_tokens:
            logger.warning(
                "Guard: token budget exceeded (%d/%d)",
                self._token_count, self.config.max_total_tokens,
            )
            return False
        return True

    def check_tool_call(self, tool_name: str) -> bool:
        """Check if a tool call is allowed. Returns False if blocked."""
        self._tool_call_count += 1

        if self._tool_call_count > self.config.max_tool_calls:
            logger.warning("Guard: tool call limit reached (%d)", self._tool_call_count)
            return False

        if tool_name in self.config.require_approval_for and not self.config.allow_destructive:
            logger.warning("Guard: tool '%s' requires approval", tool_name)
            return False

        return True

    @property
    def stats(self) -> dict:
        """Get current execution stats."""
        elapsed = 0.0
        if self._start_time:
            elapsed = time.monotonic() - self._start_time
        return {
            "iterations": self._iteration_count,
            "tokens": self._token_count,
            "tool_calls": self._tool_call_count,
            "elapsed_seconds": round(elapsed, 2),
        }


async def guarded_execute(
    fn: Callable[..., Coroutine],
    guard: ExecutionGuard,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute an async function with timeout guard.

    Usage:
        guard = ExecutionGuard()
        guard.start()
        result = await guarded_execute(my_async_fn, guard, arg1, arg2)
    """
    remaining = max(1, guard.config.max_timeout_seconds)
    if guard._start_time:
        elapsed = time.monotonic() - guard._start_time
        remaining = max(1, guard.config.max_timeout_seconds - elapsed)

    try:
        return await asyncio.wait_for(fn(*args, **kwargs), timeout=remaining)
    except asyncio.TimeoutError:
        logger.error("Guarded execution timed out for %s", fn.__name__)
        raise
