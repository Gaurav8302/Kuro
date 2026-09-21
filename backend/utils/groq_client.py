"""
Groq API Client — OpenAI-compatible chat completions.

Uses the central active_models configuration for primary → fallback attempts.
Retired model ids are remapped before any network call.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from config.active_models import (
    FALLBACK_CHAT_MODEL,
    PRIMARY_CHAT_MODEL,
    fallback_chain,
    resolve_model_id,
)
from llm.errors import LLMProviderError
from reliability.circuit_breaker import allow_request, record_failure, record_success
from utils.token_estimator import estimate_tokens, trim_messages

load_dotenv()
logger = logging.getLogger(__name__)


class GroqClient:
    """Groq OpenAI-compatible chat client with primary → fallback attempts."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

        self.base_url = "https://api.groq.com/openai/v1"
        self.model = PRIMARY_CHAT_MODEL
        self.default_params = {
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False,
        }
        logger.info("Groq client initialized (primary=%s fallback=%s)", PRIMARY_CHAT_MODEL, FALLBACK_CHAT_MODEL)

    def _prepare_messages(self, prompt: str, system_instruction: Optional[str]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _call_api(self, model: str, messages: List[Dict[str, str]], params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"model": model, "messages": messages, **params}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "60")
            raise LLMProviderError(
                f"RATE_LIMIT_EXCEEDED:Retry after {retry_after} seconds",
                model=model,
                status_code=429,
            )
        if response.status_code == 401:
            raise LLMProviderError("AUTHENTICATION_ERROR:Invalid API key", model=model, status_code=401)
        if response.status_code == 403:
            raise LLMProviderError("QUOTA_EXCEEDED:API quota exceeded", model=model, status_code=403)
        if response.status_code == 404:
            raise LLMProviderError(
                f"MODEL_NOT_FOUND:{model}",
                model=model,
                status_code=404,
            )
        if response.status_code >= 500:
            raise LLMProviderError("SERVER_ERROR:Groq server error", model=model, status_code=502)
        response.raise_for_status()
        return response.json()

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        intent: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """Generate text. Tries primary then fallback. Raises LLMProviderError on total failure."""
        del intent  # Intent-based re-routing removed; caller chooses the model.
        messages = self._prepare_messages(prompt, system_instruction)
        est_tokens = estimate_tokens(" ".join(m["content"] for m in messages))
        # Leave headroom for completion; default context for gpt-oss models is large.
        messages = trim_messages(messages, max(2048, 32000 - est_tokens - 1024))

        chain = fallback_chain(model_id)
        last_error: Optional[Exception] = None
        response_data = None
        used_model = chain[0]

        for attempt_model in chain:
            used_model = attempt_model
            if not allow_request(attempt_model):
                logger.warning("Circuit open for %s; trying next model", attempt_model)
                continue
            try:
                logger.info("Groq attempt model=%s", attempt_model)
                response_data = self._call_api(attempt_model, messages, self.default_params)
                record_success(attempt_model)
                break
            except Exception as exc:
                record_failure(attempt_model)
                last_error = exc
                logger.error("Groq attempt failed model=%s error=%s", attempt_model, exc)
                continue

        if response_data is None:
            if isinstance(last_error, LLMProviderError):
                raise last_error
            raise LLMProviderError(
                str(last_error) if last_error else "MODEL_ROUTING_FAILED:No model succeeded",
                model=used_model,
                status_code=502,
            )

        choices = response_data.get("choices") or []
        if not choices:
            raise LLMProviderError("No choices in Groq API response", model=used_model, status_code=502)

        content = choices[0].get("message", {}).get("content")
        if content is None or not str(content).strip():
            raise LLMProviderError("Empty content in Groq API response", model=used_model, status_code=502)
        return str(content).strip()

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        params = {**self.default_params, **kwargs}
        model = resolve_model_id(params.pop("model", None) or self.model)
        return self._call_api(model, messages, params)


class GroqResponse:
    def __init__(self, text: str):
        self.text = text


try:
    groq_client = GroqClient()
    logger.info("Global Groq client initialized")
except Exception as e:
    logger.error("Failed to initialize Groq client: %s", e)
    groq_client = None


def generate_with_groq(prompt: str, system_instruction: Optional[str] = None) -> GroqResponse:
    if not groq_client:
        raise LLMProviderError("Groq client not initialized", status_code=503)
    content = groq_client.generate_content(prompt, system_instruction)
    return GroqResponse(content)
