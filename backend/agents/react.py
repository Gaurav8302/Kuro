"""
ReAct Agent — Reasoning + Acting Loop

Implements the ReAct pattern (Reason → Act → Observe → Repeat)
for multi-step tool use. The agent can use tools iteratively
to solve complex tasks that require multiple steps.

Safety guards:
  - Max iterations (default: 10)
  - Total timeout (default: 120s)
  - Token budget (default: 50K total)
  - Approval gates for destructive tools
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from agents.tools.executor import ToolExecutor, ExecutionResult
from agents.tools.registry import ToolRegistry, get_tool_registry
from llm.types import LLMRequest, LLMResponse, Message, Role

logger = logging.getLogger(__name__)


class AgentResult:
    """Final result from a ReAct agent execution."""

    __slots__ = (
        "response", "tool_calls_made", "iterations",
        "total_tokens", "total_time_ms", "stopped_reason",
    )

    def __init__(
        self,
        response: str = "",
        tool_calls_made: int = 0,
        iterations: int = 0,
        total_tokens: int = 0,
        total_time_ms: int = 0,
        stopped_reason: str = "completed",
    ):
        self.response = response
        self.tool_calls_made = tool_calls_made
        self.iterations = iterations
        self.total_tokens = total_tokens
        self.total_time_ms = total_time_ms
        self.stopped_reason = stopped_reason


class ReActAgent:
    """ReAct agent with tool use and safety guards.

    Usage:
        agent = ReActAgent(llm_provider=my_provider)
        result = await agent.run(
            task="Find the weather in Tokyo",
            tools=["web_search", "calculator"],
        )
    """

    # Hard safety limits
    MAX_ITERATIONS = 10
    MAX_TIMEOUT_SECONDS = 120
    MAX_TOKEN_BUDGET = 50000

    def __init__(
        self,
        llm_provider: Any,  # LLMProvider instance
        tool_registry: Optional[ToolRegistry] = None,
        max_iterations: int = 10,
        max_timeout: int = 120,
    ):
        self.llm = llm_provider
        self.registry = tool_registry or get_tool_registry()
        self.executor = ToolExecutor(self.registry)
        self.max_iterations = min(max_iterations, self.MAX_ITERATIONS)
        self.max_timeout = min(max_timeout, self.MAX_TIMEOUT_SECONDS)

    async def run(
        self,
        task: str,
        system_prompt: str = "",
        context: Optional[List[Message]] = None,
        available_tools: Optional[List[str]] = None,
    ) -> AgentResult:
        """Run the ReAct loop to complete a task.

        Args:
            task: The task description for the agent.
            system_prompt: System prompt for the agent.
            context: Optional conversation context.
            available_tools: Tool names to make available (None = all).

        Returns:
            AgentResult with the final response and execution metrics.
        """
        start_time = time.monotonic()
        total_tokens = 0
        tool_calls_made = 0

        # Build initial messages
        messages: List[Message] = []
        if system_prompt:
            messages.append(Message(role=Role.SYSTEM, content=system_prompt))
        else:
            messages.append(Message(role=Role.SYSTEM, content=self._default_system_prompt()))

        if context:
            messages.extend(context)

        messages.append(Message(role=Role.USER, content=task))

        # Build tool descriptions for the prompt
        tool_specs = self.registry.list_tools()
        if available_tools:
            tool_specs = [t for t in tool_specs if t.name in available_tools]

        if tool_specs:
            tool_desc = "\n".join(
                f"- {t.name}: {t.description}" for t in tool_specs
            )
            messages.append(Message(
                role=Role.SYSTEM,
                content=(
                    f"Available tools:\n{tool_desc}\n\n"
                    "To use a tool, respond with:\n"
                    "TOOL: <tool_name>\n"
                    "ARGS: <json_arguments>\n\n"
                    "After receiving tool results, continue reasoning.\n"
                    "When done, respond with your final answer (no TOOL prefix)."
                ),
            ))

        for iteration in range(self.max_iterations):
            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > self.max_timeout:
                return AgentResult(
                    response="Agent stopped: timeout exceeded.",
                    tool_calls_made=tool_calls_made,
                    iterations=iteration,
                    total_tokens=total_tokens,
                    total_time_ms=int(elapsed * 1000),
                    stopped_reason="timeout",
                )

            # Check token budget
            if total_tokens >= self.MAX_TOKEN_BUDGET:
                return AgentResult(
                    response="Agent stopped: token budget exceeded.",
                    tool_calls_made=tool_calls_made,
                    iterations=iteration,
                    total_tokens=total_tokens,
                    total_time_ms=int(elapsed * 1000),
                    stopped_reason="token_budget",
                )

            # Generate
            request = LLMRequest(messages=messages)
            response = await self.llm.generate(request)
            total_tokens += response.token_count

            content = (response.content or "").strip()

            # Check if agent wants to use a tool
            tool_call = self._parse_tool_call(content)
            if tool_call is None:
                # No tool call — this is the final answer
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return AgentResult(
                    response=content,
                    tool_calls_made=tool_calls_made,
                    iterations=iteration + 1,
                    total_tokens=total_tokens,
                    total_time_ms=elapsed_ms,
                    stopped_reason="completed",
                )

            # Execute the tool
            tool_name, tool_args = tool_call
            result = await self.executor.execute(tool_name, tool_args)
            tool_calls_made += 1

            # Add the assistant's reasoning and tool result to context
            messages.append(Message(role=Role.ASSISTANT, content=content))
            messages.append(Message(
                role=Role.USER,
                content=f"Tool result ({tool_name}):\n{result.to_string()}",
                name="tool_result",
            ))

        # Exhausted iterations
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return AgentResult(
            response="Agent stopped: maximum iterations reached.",
            tool_calls_made=tool_calls_made,
            iterations=self.max_iterations,
            total_tokens=total_tokens,
            total_time_ms=elapsed_ms,
            stopped_reason="max_iterations",
        )

    @staticmethod
    def _parse_tool_call(content: str) -> Optional[tuple]:
        """Parse a tool call from agent output.

        Expected format:
            TOOL: <name>
            ARGS: <json>
        """
        import json as _json

        lines = content.strip().split("\n")
        tool_name = None
        args_str = None

        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith("TOOL:"):
                tool_name = stripped[5:].strip()
            elif stripped.upper().startswith("ARGS:"):
                args_str = stripped[5:].strip()

        if not tool_name:
            return None

        try:
            args = _json.loads(args_str) if args_str else {}
        except (_json.JSONDecodeError, TypeError):
            args = {}

        return (tool_name, args)

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "You are a helpful AI agent that can use tools to accomplish tasks.\n"
            "Think step by step. Use tools when needed.\n"
            "When you have enough information to answer, provide your final response.\n"
            "Do NOT use a tool if you can answer directly."
        )
