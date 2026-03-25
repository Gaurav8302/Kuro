"""Backward-compatible chat manager module.

This shim preserves imports of ``memory.chat_manager`` used by legacy tests/scripts.
"""

from memory.chat_manager_v2 import ChatManager, chat_manager, chat_with_memory

__all__ = ["ChatManager", "chat_manager", "chat_with_memory"]
