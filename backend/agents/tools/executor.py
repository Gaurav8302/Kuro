"""
Tool Executor — Sandboxed Tool Execution

Executes tool calls with timeout guards, error isolation,
and optional approval gates. Ensures no tool can crash the
main pipeline or run indefinitely.
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Dict, Optional

from agents.tools.registry import ToolRegistry, ToolSpec, get_tool_registry

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of a tool execution."""

    __slots__ = ("tool_name", "output", "error", "duration_ms", "approved")

    def __init__(
        self,
        tool_name: str,
        output: Any = None,
        error: Optional[str] = None,
        duration_ms: int = 0,
        approved: bool = True,
    ):
        self.tool_name = tool_name
        self.output = output
        self.error = error
        self.duration_ms = duration_ms
        self.approved = approved

    @property
    def success(self) -> bool:
        return self.error is None and self.approved

    def to_string(self) -> str:
        """Convert result to string for LLM consumption."""
        if not self.approved:
            return f"[BLOCKED] Tool '{self.tool_name}' requires approval."
        if self.error:
            return f"[ERROR] Tool '{self.tool_name}' failed: {self.error}"
        return str(self.output or "")


class ToolExecutor:
    """Executes tools with safety guards."""

    # Hard limits
    MAX_TIMEOUT = 60  # seconds
    DEFAULT_TIMEOUT = 30  # seconds

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_tool_registry()

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        require_approval: bool = False,
    ) -> ExecutionResult:
        """Execute a tool by name with arguments.

        Args:
            tool_name: Name of the registered tool.
            arguments: Arguments to pass to the tool handler.
            require_approval: If True, block execution (for dangerous tools).

        Returns:
            ExecutionResult with output or error.
        """
        spec = self.registry.get(tool_name)
        if spec is None:
            return ExecutionResult(
                tool_name=tool_name,
                error=f"Tool '{tool_name}' not found in registry",
            )

        # Check approval gate
        if spec.requires_approval or require_approval:
            logger.warning("Tool '%s' requires approval — blocking execution", tool_name)
            return ExecutionResult(
                tool_name=tool_name,
                approved=False,
            )

        timeout = min(spec.timeout_seconds, self.MAX_TIMEOUT)
        start = time.monotonic()

        try:
            if asyncio.iscoroutinefunction(spec.handler):
                result = await asyncio.wait_for(
                    spec.handler(**arguments),
                    timeout=timeout,
                )
            else:
                # Run sync handlers in a thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: spec.handler(**arguments)),
                    timeout=timeout,
                )

            duration_ms = int((time.monotonic() - start) * 1000)

            return ExecutionResult(
                tool_name=tool_name,
                output=result,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("Tool '%s' timed out after %dms", tool_name, duration_ms)
            return ExecutionResult(
                tool_name=tool_name,
                error=f"Timeout after {timeout}s",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            tb = traceback.format_exc()
            logger.error("Tool '%s' failed: %s\n%s", tool_name, e, tb)
            return ExecutionResult(
                tool_name=tool_name,
                error=str(e),
                duration_ms=duration_ms,
            )
