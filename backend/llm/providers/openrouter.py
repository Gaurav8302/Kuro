"""
OpenRouter LLM Provider

Implements LLMProvider for OpenRouter's unified API.
Supports Claude, GPT-4, Mistral, LLaMA, and many more models
through a single endpoint.
"""

import os
import time
import logging
from typing import List, Optional

import httpx

from llm.provider import (
    LLMProvider, LLMError, AuthenticationError, RateLimitError,
)
from llm.types import (
    LLMRequest, LLMResponse, ModelInfo, ProviderType, Role,
)

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider — access 100+ models through one endpoint."""

    provider_type = ProviderType.OPENROUTER

    MODELS = {
        "meta-llama/llama-3.1-70b-instruct": ModelInfo(
            name="meta-llama/llama-3.1-70b-instruct",
            provider=ProviderType.OPENROUTER,
            context_window=131072,
            cost_per_1k_input=0.00035,
            cost_per_1k_output=0.0004,
        ),
        "anthropic/claude-3.5-sonnet": ModelInfo(
            name="anthropic/claude-3.5-sonnet",
            provider=ProviderType.OPENROUTER,
            context_window=200000,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
        "google/gemini-pro-1.5": ModelInfo(
            name="google/gemini-pro-1.5",
            provider=ProviderType.OPENROUTER,
            context_window=1000000,
            cost_per_1k_input=0.00125,
            cost_per_1k_output=0.005,
        ),
        "mistralai/mistral-large": ModelInfo(
            name="mistralai/mistral-large",
            provider=ProviderType.OPENROUTER,
            context_window=128000,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.006,
        ),
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def get_default_model(self) -> str:
        return "meta-llama/llama-3.1-70b-instruct"

    def list_models(self) -> List[ModelInfo]:
        return list(self.MODELS.values())

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise AuthenticationError("OPENROUTER_API_KEY not set", ProviderType.OPENROUTER)

        model = request.model or self.get_default_model()
        messages = [msg.to_dict() for msg in request.messages]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 2048,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kuro-ai.vercel.app",
            "X-Title": "Kuro AI",
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers, json=payload,
                )
            if resp.status_code == 401:
                raise AuthenticationError("Invalid OpenRouter API key", ProviderType.OPENROUTER)
            if resp.status_code == 429:
                raise RateLimitError("OpenRouter rate limit exceeded", ProviderType.OPENROUTER)
            resp.raise_for_status()

            data = resp.json()
            latency_ms = int((time.monotonic() - start) * 1000)

            content = ""
            if data.get("choices"):
                content = data["choices"][0].get("message", {}).get("content", "")

            return LLMResponse(
                content=content, model=model,
                usage=data.get("usage"), latency_ms=latency_ms,
            )
        except (AuthenticationError, RateLimitError):
            raise
        except Exception as e:
            raise LLMError(f"OpenRouter request failed: {e}", ProviderType.OPENROUTER)
