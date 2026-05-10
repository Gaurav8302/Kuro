"""
Lifecycle Hooks — Extensible Event-Driven Processing

Inspired by ECC's hooks.json architecture. Allows registering
pre/post handlers for key lifecycle events without modifying
core pipeline code.

Supported hook points:
  - pre_chat      : Before processing a chat message
  - post_chat     : After generating a response
  - pre_memory    : Before memory retrieval
  - post_memory   : After memory retrieval
  - pre_tool      : Before tool execution
  - post_tool     : After tool execution
  - session_start : When a new session begins
  - session_end   : When a session ends
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class HookPoint(str, Enum):
    """Supported hook points in the lifecycle."""
    PRE_CHAT = "pre_chat"
    POST_CHAT = "post_chat"
    PRE_MEMORY = "pre_memory"
    POST_MEMORY = "post_memory"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class HookContext:
    """Context passed to hook handlers."""
    hook_point: HookPoint
    data: Dict[str, Any]
    # Hooks can set this to True to abort the operation
    abort: bool = False
    abort_reason: str = ""


# Handler type
HookHandler = Union[
    Callable[[HookContext], None],
    Callable[[HookContext], Coroutine[Any, Any, None]],
]


class HookRegistry:
    """Registry for lifecycle hooks."""

    def __init__(self):
        self._hooks: Dict[HookPoint, List[HookHandler]] = {
            point: [] for point in HookPoint
        }

    def register(self, point: HookPoint, handler: HookHandler) -> None:
        """Register a handler for a hook point."""
        self._hooks[point].append(handler)
        logger.debug("Registered hook: %s -> %s", point.value, handler.__name__)

    def unregister(self, point: HookPoint, handler: HookHandler) -> None:
        """Remove a handler from a hook point."""
        handlers = self._hooks.get(point, [])
        if handler in handlers:
            handlers.remove(handler)

    async def execute(self, point: HookPoint, data: Dict[str, Any]) -> HookContext:
        """Execute all handlers for a hook point.

        Args:
            point: The hook point to execute.
            data: Context data to pass to handlers.

        Returns:
            HookContext with potentially modified data and abort flag.
        """
        ctx = HookContext(hook_point=point, data=data)
        handlers = self._hooks.get(point, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(ctx)
                else:
                    handler(ctx)

                # If any handler aborts, stop executing further hooks
                if ctx.abort:
                    logger.warning(
                        "Hook '%s' aborted by %s: %s",
                        point.value, handler.__name__, ctx.abort_reason,
                    )
                    break
            except Exception as e:
                logger.error(
                    "Hook handler %s failed at '%s': %s",
                    handler.__name__, point.value, e,
                )

        return ctx

    def clear(self, point: Optional[HookPoint] = None) -> None:
        """Clear all handlers for a hook point (or all points)."""
        if point:
            self._hooks[point] = []
        else:
            self._hooks = {p: [] for p in HookPoint}


# Global singleton
_hook_registry: Optional[HookRegistry] = None


def get_hook_registry() -> HookRegistry:
    """Get or create the global hook registry."""
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = HookRegistry()
    return _hook_registry
