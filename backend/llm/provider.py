"""
LLM Provider — Abstract Base Class

Defines the contract that all LLM providers must implement.
Enables swapping between Groq, OpenRouter, Gemini, or local
models without changing any calling code.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from llm.types import LLMRequest, LLMResponse, ModelInfo, ProviderType

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_type: ProviderType

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            request: Typed LLM request with messages, model, params.

        Returns:
            Typed LLM response with content, usage, latency.
        """
        ...

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models for this provider."""
        ...

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that the provider is properly configured."""
        ...

    def get_default_model(self) -> str:
        """Return the default model ID for this provider."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_default_model"
        )


class LLMError(Exception):
    """Base exception for LLM operations."""

    def __init__(
        self,
        message: str,
        provider: Optional[ProviderType] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.code = code


class AuthenticationError(LLMError):
    """API key invalid or missing."""
    ...


class RateLimitError(LLMError):
    """Provider rate limit exceeded."""
    ...


class ContextLengthError(LLMError):
    """Input exceeds model context window."""
    ...


class ModelNotFoundError(LLMError):
    """Requested model does not exist."""
    ...
