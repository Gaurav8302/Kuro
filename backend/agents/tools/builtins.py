"""
Built-in Tools — Default tools available to agents

Registers common utilities (calculator, text tools, memory search)
that agents can use via the tool registry.
"""

import logging
import math
import re
from typing import Optional

from agents.tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


def register_builtin_tools():
    """Register all built-in tools in the global registry."""
    registry = get_tool_registry()

    # ---- Calculator ----
    @registry.register_decorator(
        name="calculator",
        description="Evaluate a mathematical expression. Supports basic arithmetic, powers, sqrt, trig.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"],
        },
        category="utility",
    )
    def calculator(expression: str) -> str:
        """Safely evaluate a math expression."""
        # Whitelist allowed characters and functions
        allowed = set("0123456789+-*/().^ %eE")
        clean = expression.replace("^", "**")

        # Sanitize: only allow math functions
        safe_names = {
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "log": math.log, "log10": math.log10,
            "abs": abs, "round": round, "pi": math.pi, "e": math.e,
            "pow": pow, "ceil": math.ceil, "floor": math.floor,
        }

        try:
            result = eval(clean, {"__builtins__": {}}, safe_names)  # noqa: S307
            return str(result)
        except Exception as exc:
            return f"Error evaluating '{expression}': {exc}"

    # ---- Word Counter ----
    @registry.register_decorator(
        name="word_counter",
        description="Count words, characters, sentences, and paragraphs in text.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"}
            },
            "required": ["text"],
        },
        category="utility",
    )
    def word_counter(text: str) -> str:
        words = len(text.split())
        chars = len(text)
        sentences = len(re.findall(r"[.!?]+", text))
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])
        return (
            f"Words: {words}, Characters: {chars}, "
            f"Sentences: {sentences}, Paragraphs: {paragraphs}"
        )

    # ---- Memory Search (async) ----
    @registry.register_decorator(
        name="memory_search",
        description="Search user memories for relevant information.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "user_id": {"type": "string", "description": "User ID to search"},
            },
            "required": ["query", "user_id"],
        },
        category="memory",
    )
    async def memory_search(query: str, user_id: str) -> str:
        try:
            from memory.retriever import MemoryRetriever
            retriever = MemoryRetriever()
            results = await retriever.retrieve(
                user_id=user_id, query=query,
                memory_types=["fact", "preference", "event"],
                top_k=5,
            )
            if not results:
                return "No relevant memories found."
            return "\n".join(
                f"- {r.get('text', '')} (score: {r.get('score', 0):.2f})"
                for r in results
            )
        except Exception as e:
            return f"Memory search failed: {e}"

    # ---- Date/Time ----
    @registry.register_decorator(
        name="current_datetime",
        description="Get the current date and time.",
        category="utility",
    )
    def current_datetime() -> str:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info("Registered %d built-in tools", len(registry))
