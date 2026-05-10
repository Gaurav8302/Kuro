"""
Gemini LLM Provider

Implements LLMProvider for Google's Gemini API.
Uses the google-generativeai SDK for generation.
"""

import os
import time
import logging
from typing import List, Optional

from llm.provider import (
    LLMProvider, LLMError, AuthenticationError, RateLimitError,
)
from llm.types import (
    LLMRequest, LLMResponse, ModelInfo, ProviderType, Role,
)

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    provider_type = ProviderType.GEMINI

    MODELS = {
        "gemini-2.0-flash": ModelInfo(
            name="gemini-2.0-flash",
            provider=ProviderType.GEMINI,
            context_window=1048576,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
        "gemini-1.5-pro": ModelInfo(
            name="gemini-1.5-pro",
            provider=ProviderType.GEMINI,
            context_window=1048576,
            cost_per_1k_input=0.00125,
            cost_per_1k_output=0.005,
        ),
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def get_default_model(self) -> str:
        return "gemini-2.0-flash"

    def list_models(self) -> List[ModelInfo]:
        return list(self.MODELS.values())

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise AuthenticationError("GEMINI_API_KEY not set", ProviderType.GEMINI)

        try:
            import google.generativeai as genai
        except ImportError:
            raise LLMError("google-generativeai package not installed", ProviderType.GEMINI)

        genai.configure(api_key=self.api_key)
        model_name = request.model or self.get_default_model()

        # Convert messages to Gemini format
        # Gemini uses a different format: system instruction + contents
        system_parts = []
        contents = []
        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                system_parts.append(msg.content)
            elif msg.role == Role.USER:
                contents.append({"role": "user", "parts": [msg.content]})
            elif msg.role == Role.ASSISTANT:
                contents.append({"role": "model", "parts": [msg.content]})

        generation_config = {
            "temperature": request.temperature,
        }
        if request.max_tokens:
            generation_config["max_output_tokens"] = request.max_tokens

        start = time.monotonic()
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction="\n".join(system_parts) if system_parts else None,
                generation_config=generation_config,
            )

            if contents:
                response = model.generate_content(contents)
            else:
                response = model.generate_content("Hello")

            latency_ms = int((time.monotonic() - start) * 1000)
            content = response.text if hasattr(response, "text") else str(response)

            usage = None
            if hasattr(response, "usage_metadata"):
                meta = response.usage_metadata
                usage = {
                    "prompt_tokens": getattr(meta, "prompt_token_count", 0),
                    "completion_tokens": getattr(meta, "candidates_token_count", 0),
                    "total_tokens": getattr(meta, "total_token_count", 0),
                }

            return LLMResponse(
                content=content, model=model_name,
                usage=usage, latency_ms=latency_ms,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str:
                raise RateLimitError(f"Gemini rate limit: {e}", ProviderType.GEMINI)
            if "401" in err_str or "api_key" in err_str:
                raise AuthenticationError(f"Gemini auth error: {e}", ProviderType.GEMINI)
            raise LLMError(f"Gemini generation failed: {e}", ProviderType.GEMINI)
