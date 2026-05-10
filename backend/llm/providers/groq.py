"""
Groq LLM Provider — Concrete Implementation

Implements LLMProvider for Groq's API (LLaMA, Mixtral, DeepSeek).
Uses the OpenAI-compatible chat completions endpoint.
"""

import os
import time
import logging
from typing import List, Optional

import requests

from llm.provider import (
    LLMProvider,
    LLMError,
    AuthenticationError,
    RateLimitError,
)
from llm.types import (
    LLMRequest,
    LLMResponse,
    Message,
    ModelInfo,
    ProviderType,
    Role,
)

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """Groq API provider using OpenAI-compatible chat completions."""

    provider_type = ProviderType.GROQ

    # Canonical model registry
    MODELS = {
        "llama-3.1-8b-instant": ModelInfo(
            name="llama-3.1-8b-instant",
            provider=ProviderType.GROQ,
            context_window=8192,
            max_tokens=1024,
        ),
        "llama-3.3-70b-versatile": ModelInfo(
            name="llama-3.3-70b-versatile",
            provider=ProviderType.GROQ,
            context_window=32768,
            max_tokens=4096,
        ),
        "mixtral-8x7b-32768": ModelInfo(
            name="mixtral-8x7b-32768",
            provider=ProviderType.GROQ,
            context_window=32768,
            max_tokens=4096,
        ),
        "deepseek-r1-distill-llama-70b": ModelInfo(
            name="deepseek-r1-distill-llama-70b",
            provider=ProviderType.GROQ,
            context_window=32768,
            max_tokens=4096,
        ),
    }

    # Aliases for backward compatibility
    _ALIASES = {
        "mixtral-8x7b-32k": "mixtral-8x7b-32768",
        "llama3-8b-8192": "llama-3.1-8b-instant",
        "llama3-70b-8192": "llama-3.3-70b-versatile",
        "deepseek-r1": "deepseek-r1-distill-llama-70b",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.base_url = "https://api.groq.com/openai/v1"

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def get_default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    def list_models(self) -> List[ModelInfo]:
        return list(self.MODELS.values())

    def _resolve_model(self, model_id: Optional[str]) -> str:
        """Resolve model aliases to canonical IDs."""
        if not model_id:
            return self.get_default_model()
        return self._ALIASES.get(model_id, model_id)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response via Groq's API."""
        if not self.api_key:
            raise AuthenticationError("GROQ_API_KEY not set", ProviderType.GROQ)

        model = self._resolve_model(request.model)
        model_info = self.MODELS.get(model)
        max_tokens = request.max_tokens or (model_info.max_tokens if model_info else 1024)

        messages = [msg.to_dict() for msg in request.messages]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if resp.status_code == 401:
                raise AuthenticationError("Invalid Groq API key", ProviderType.GROQ)
            if resp.status_code == 429:
                raise RateLimitError("Groq rate limit exceeded", ProviderType.GROQ)
            resp.raise_for_status()

            data = resp.json()
            latency_ms = int((time.monotonic() - start) * 1000)

            content = ""
            if data.get("choices"):
                content = data["choices"][0].get("message", {}).get("content", "")

            usage = data.get("usage")

            return LLMResponse(
                content=content,
                model=model,
                usage=usage,
                latency_ms=latency_ms,
            )

        except (AuthenticationError, RateLimitError):
            raise
        except requests.exceptions.RequestException as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            raise LLMError(
                f"Groq API request failed: {e}",
                provider=ProviderType.GROQ,
                code="REQUEST_FAILED",
            )


# Convenience: quick-generate function
async def groq_generate(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """Quick generate helper for simple prompt→response use cases."""
    provider = GroqProvider()
    request = LLMRequest(
        messages=[Message(role=Role.USER, content=prompt)],
        model=model,
    )
    response = await provider.generate(request)
    return response.content
