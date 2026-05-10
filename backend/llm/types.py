"""
LLM Types — Typed Input/Output for LLM Operations

Provides clean, typed dataclasses for all LLM interactions,
inspired by ECC's type system but adapted for Kuro's Python backend.
Eliminates raw dict passing and ensures consistent interfaces
across all LLM providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Role(str, Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProviderType(str, Enum):
    """Supported LLM providers."""
    GROQ = "groq"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"


@dataclass(frozen=True)
class Message:
    """A single message in a conversation."""
    role: Role
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass(frozen=True)
class ToolDefinition:
    """Definition of a tool that can be called by the LLM."""
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """Result of executing a tool call."""
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class LLMRequest:
    """Input to an LLM provider."""
    messages: List[Message]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[List[ToolDefinition]] = None
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "messages": [msg.to_dict() for msg in self.messages],
            "temperature": self.temperature,
        }
        if self.model:
            result["model"] = self.model
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.tools:
            result["tools"] = [tool.to_dict() for tool in self.tools]
        return result


@dataclass
class LLMResponse:
    """Output from an LLM provider."""
    content: str
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[ToolCall]] = None
    latency_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def token_count(self) -> int:
        if self.usage:
            return self.usage.get("total_tokens", 0)
        return 0


@dataclass(frozen=True)
class ModelInfo:
    """Information about an available model."""
    name: str
    provider: ProviderType
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    supports_tools: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
