"""
Event Bus — Lightweight Async Pub/Sub

Simple event system for decoupling cross-cutting concerns like
logging, metrics, memory updates, and session lifecycle management
from the main chat pipeline.

Usage:
    bus = EventBus()
    bus.on("chat.responded", my_handler)
    await bus.emit(Event("chat.responded", {"user_id": "...", "message": "..."}))
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Union

logger = logging.getLogger(__name__)

# Handler type: can be sync or async
EventHandler = Union[Callable[..., None], Callable[..., Coroutine]]


@dataclass
class Event:
    """An event with a name and arbitrary data payload."""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Lightweight async event bus with fire-and-forget semantics.

    Handlers are invoked as async tasks and do not block the caller.
    Errors in handlers are logged but never propagate to the emitter.
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}

    def on(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers.setdefault(event_name, []).append(handler)

    def off(self, event_name: str, handler: EventHandler) -> None:
        """Unregister a handler."""
        handlers = self._handlers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: Event) -> None:
        """Emit an event — all handlers run as background tasks."""
        handlers = self._handlers.get(event.name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(self._safe_call_async(handler, event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    "Error dispatching event '%s' to handler %s: %s",
                    event.name, handler.__name__, e,
                )

    @staticmethod
    async def _safe_call_async(handler: Callable, event: Event) -> None:
        """Call an async handler with error isolation."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "Async handler %s failed for event '%s': %s",
                handler.__name__, event.name, e,
            )


# Global singleton
event_bus = EventBus()
