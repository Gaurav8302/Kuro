"""
Base Agent — Abstract Agent Definition

Provides the contract for all agent types (ReAct, Plan-and-Execute, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from llm.types import Message


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    async def run(
        self,
        task: str,
        system_prompt: str = "",
        context: Optional[List[Message]] = None,
        available_tools: Optional[List[str]] = None,
    ) -> Any:
        """Execute the agent's task and return a result."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this agent type."""
        ...
