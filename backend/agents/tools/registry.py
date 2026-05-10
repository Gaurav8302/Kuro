"""
Tool Registry — Centralized Tool Management

Manages available tools that agents can invoke. Each tool is a
callable with typed parameters and a description. Inspired by
ECC's ToolRegistry pattern but adapted for Python async.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Tool handler can be sync or async
ToolHandler = Union[
    Callable[..., Any],
    Callable[..., Coroutine[Any, Any, Any]],
]


@dataclass
class ToolSpec:
    """Specification for a registered tool."""
    name: str
    description: str
    handler: ToolHandler
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    timeout_seconds: int = 30
    category: str = "general"

    def to_llm_schema(self) -> Dict[str, Any]:
        """Convert to LLM-compatible tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                },
            },
        }


class ToolRegistry:
    """Registry for all available agent tools."""

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: ToolHandler,
        parameters: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False,
        timeout_seconds: int = 30,
        category: str = "general",
    ) -> None:
        """Register a new tool."""
        spec = ToolSpec(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {},
            requires_approval=requires_approval,
            timeout_seconds=timeout_seconds,
            category=category,
        )
        self._tools[name] = spec
        logger.debug("Registered tool: %s (category=%s)", name, category)

    def register_decorator(
        self,
        name: Optional[str] = None,
        description: str = "",
        **kwargs: Any,
    ) -> Callable:
        """Decorator to register a function as a tool.

        Usage:
            @registry.register_decorator(description="Search the web")
            async def web_search(query: str) -> str:
                ...
        """
        def decorator(fn: ToolHandler) -> ToolHandler:
            tool_name = name or fn.__name__
            tool_desc = description or fn.__doc__ or ""
            self.register(tool_name, tool_desc, fn, **kwargs)
            return fn
        return decorator

    def get(self, name: str) -> Optional[ToolSpec]:
        """Get a tool specification by name."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolSpec]:
        """List all registered tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_llm_schemas(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tool schemas in LLM-compatible format."""
        return [tool.to_llm_schema() for tool in self.list_tools(category)]

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Global default registry
_default_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry
