"""
OpenRouter API client

Provides a simple interface compatible with our orchestrator to call
OpenRouter's chat completions API. Maps our canonical model IDs to
OpenRouter provider slugs. Supports overrides via OPENROUTER_MODEL_MAP
(JSON string).
"""
from __future__ import annotations
import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv
import time

load_dotenv()
logger = logging.getLogger(__name__)

# Default base URL
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# Canonical -> OpenRouter slug mapping (updated with actual available models)
DEFAULT_MODEL_MAP: Dict[str, str] = {
    # High-quality reasoning models
    "deepseek-r1": "deepseek/r1",
    "deepseek-r1-distill": "deepseek/r1-distill-qwen-14b",
    
    # Fast, reliable models
    "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
    "llama-3.2-3b": "meta-llama/llama-3.2-3b-instruct", 
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    
    # Google models
    "gemini-2.0-flash": "google/gemini-2.0-flash-exp:free",
    "gemini-2.5-pro": "google/gemini-2.5-pro-exp:free",
    
    # Specialized models
    "mistral-nemo": "mistralai/mistral-nemo",
    "qwen3-coder": "qwen/qwen-3-coder-480b-a35b",
    
    # Legacy mappings for backward compatibility
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-haiku": "anthropic/claude-3-haiku",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4o": "openai/gpt-4o-mini",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "mixtral-8x7b-openrouter": "mistralai/mixtral-8x7b-instruct",
    "llama-3-70b-openrouter": "meta-llama/llama-3-70b-instruct",
    "gemini-1.5-pro": "google/gemini-pro-1.5",
    "gemini-1.5-flash": "google/gemini-flash-1.5",
}


class OpenRouterClient:
    def __init__(self) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        self.api_key = api_key
        self.base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        # Allow overrides via JSON env
        overrides = os.getenv("OPENROUTER_MODEL_MAP")
        self.model_map = DEFAULT_MODEL_MAP.copy()
        if overrides:
            try:
                self.model_map.update(json.loads(overrides))
            except Exception as e:
                logger.warning(f"Failed to parse OPENROUTER_MODEL_MAP: {e}")

    def _map_model(self, canonical_id: Optional[str]) -> str:
        if not canonical_id:
            return self.model_map.get("gpt-4o", "openai/gpt-4o-mini")
        return self.model_map.get(canonical_id, self.model_map.get("gpt-4o", "openai/gpt-4o-mini"))

    def _prepare_messages(self, prompt: str, system_instruction: Optional[str]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _call_api(self, model_slug: str, messages: List[Dict[str, str]], params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": model_slug, "messages": messages, **params}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Optional recommended headers by OpenRouter
        referer = os.getenv("OPENROUTER_REFERER")
        if referer:
            headers["HTTP-Referer"] = referer
        site = os.getenv("OPENROUTER_SITE_NAME")
        if site:
            headers["X-Title"] = site
        resp = requests.post(url, json=payload, headers=headers, timeout=45)
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after", "60")
            raise Exception(f"RATE_LIMIT_EXCEEDED:Retry after {retry_after} seconds")
        elif resp.status_code == 401:
            raise Exception("AUTHENTICATION_ERROR:Invalid API key")
        elif resp.status_code == 403:
            raise Exception("QUOTA_EXCEEDED:API quota exceeded")
        elif resp.status_code >= 500:
            raise Exception("SERVER_ERROR:OpenRouter server error")
        resp.raise_for_status()
        return resp.json()

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        intent: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> str:
        messages = self._prepare_messages(prompt, system_instruction)
        model_slug = self._map_model(model_id)
        params = {"temperature": 0.7, "max_tokens": 1024, "top_p": 1, "stream": False}
        start = time.perf_counter()
        try:
            data = self._call_api(model_slug, messages, params)
            latency_ms = int((time.perf_counter() - start) * 1000)
            # Log model usage and latency to Render logs
            logger.info(
                f"openrouter_call provider=OpenRouter canonical_model={model_id or 'auto'} model_slug={model_slug} intent={intent or ''} latency_ms={latency_ms}"
            )
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning(
                f"openrouter_call_failed provider=OpenRouter canonical_model={model_id or 'auto'} model_slug={model_slug} intent={intent or ''} latency_ms={latency_ms} error={str(e)}"
            )
            raise

        if data and "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        raise Exception("No choices in OpenRouter API response")
