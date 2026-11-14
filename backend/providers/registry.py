"""
Provider Abstraction — Unified interface for LLM providers with reliability patterns.

Provides:
- Common provider interface with standardized contracts
- Provider allowlist and configuration validation
- Fallback/retry policy with cost budget awareness
- Streaming correctness with authorization
- Stable response schema with redacted errors
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Literal
from enum import Enum

from config.active_models import (
    PRIMARY_CHAT_MODEL,
    FALLBACK_CHAT_MODEL,
    fallback_chain,
    get_role_model,
    resolve_model_id,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PROVIDER CONTRACT
# =============================================================================

class ProviderType(Enum):
    """Supported provider types."""
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class ModelCapability(Enum):
    """Model capabilities for routing."""
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"


@dataclass
class ModelInfo:
    """Model metadata."""
    model_id: str
    provider: ProviderType
    capabilities: List[ModelCapability] = field(default_factory=list)
    max_tokens: int = 8192
    context_window: int = 8192
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = False


@dataclass
class ProviderConfig:
    """Provider configuration."""
    provider_type: ProviderType
    api_key_env: str
    base_url: str
    enabled: bool = True
    timeout_seconds: int = 60
    max_retries: int = 3
    rate_limit_rpm: int = 60
    allowed_models: List[str] = field(default_factory=list)


class LLMProviderError(Exception):
    """Provider error with categorization."""
    def __init__(
        self,
        message: str,
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        status_code: int = 502,
        error_code: str = "provider_error",
        retryable: bool = True,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable
        self.retry_after = retry_after


# =============================================================================
# PROVIDER INTERFACE
# =============================================================================

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._api_key = os.getenv(config.api_key_env)
        if not self._api_key and config.enabled:
            raise ValueError(f"API key not found in env: {config.api_key_env}")
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> List[ModelInfo]:
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate completion. Returns normalized response."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream completion chunks."""
        pass
    
    def _validate_model(self, model: str) -> str:
        """Validate and resolve model ID."""
        if not self.config.enabled:
            raise LLMProviderError(
                f"Provider {self.provider_type.value} is disabled",
                provider=self.provider_type,
                status_code=503,
            )
        
        if self.config.allowed_models and model not in self.config.allowed_models:
            # Try to resolve via legacy aliases
            from config.active_models import resolve_model_id
            resolved = resolve_model_id(model)
            if resolved not in self.config.allowed_models:
                raise LLMProviderError(
                    f"Model '{model}' not allowed for provider {self.provider_type.value}",
                    provider=self.provider_type,
                    status_code=400,
                    error_code="model_not_allowed",
                )
            return resolved
        return model
    
    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a completion."""
        model_info = next((m for m in self.available_models if m.model_id == model), None)
        if model_info:
            return (input_tokens / 1000) * model_info.cost_per_1k_input + \
                   (output_tokens / 1000) * model_info.cost_per_1k_output
        return 0.0


# =============================================================================
# GROQ PROVIDER
# =============================================================================

class GroqProvider(BaseProvider):
    """Groq provider implementation."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GROQ
    
    @property
    def available_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                model_id="openai/gpt-oss-120b",
                provider=ProviderType.GROQ,
                capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
                max_tokens=8192,
                context_window=131072,
                cost_per_1k_input=0.0001,
                cost_per_1k_output=0.0001,
            ),
            ModelInfo(
                model_id="openai/gpt-oss-20b",
                provider=ProviderType.GROQ,
                capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
                max_tokens=8192,
                context_window=131072,
                cost_per_1k_input=0.00005,
                cost_per_1k_output=0.00005,
            ),
        ]
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 1.0,
        **kwargs,
    ) -> Dict[str, Any]:
        model = self._validate_model(model)
        
        import requests
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
        }
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            import requests
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
        except requests.Timeout:
            raise LLMProviderError(
                "Request timed out",
                provider=self.provider_type,
                model=model,
                error_code="timeout",
            )
        except requests.RequestException as e:
            raise LLMProviderError(
                f"Network error: {e}",
                provider=self.provider_type,
                model=model,
                status_code=502,
            )
        
        # Handle errors
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "60")
            raise LLMProviderError(
                f"RATE_LIMIT_EXCEEDED: Retry after {retry_after} seconds",
                provider=self.provider_type,
                model=model,
                status_code=429,
                error_code="rate_limit",
                retryable=True,
                retry_after=int(retry_after),
            )
        elif response.status_code == 401:
            raise LLMProviderError(
                "AUTHENTICATION_ERROR: Invalid API key",
                provider=self.provider_type,
                model=model,
                status_code=401,
                error_code="auth_error",
                retryable=False,
            )
        elif response.status_code == 403:
            raise LLMProviderError(
                "QUOTA_EXCEEDED: API quota exceeded",
                provider=self.provider_type,
                model=model,
                status_code=403,
                error_code="quota_exceeded",
                retryable=False,
            )
        elif response.status_code == 404:
            raise LLMProviderError(
                f"MODEL_NOT_FOUND: {model}",
                provider=self.provider_type,
                model=model,
                status_code=404,
                error_code="model_not_found",
                retryable=False,
            )
        elif response.status_code >= 500:
            raise LLMProviderError(
                "SERVER_ERROR: Groq server error",
                provider=self.provider_type,
                model=model,
                status_code=502,
                error_code="server_error",
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Normalize response
        return self._normalize_response(data, model)
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream completion chunks."""
        model = self._validate_model(model)
        
        import requests
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds,
                stream=True,
            )
        except Exception as e:
            raise LLMProviderError(
                f"Stream request failed: {e}",
                provider=self.provider_type,
                error_code="stream_error",
            )
        
        if response.status_code != 200:
            raise LLMProviderError(
                f"Stream error: {response.status_code}",
                provider=self.provider_type,
            )
        
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data_str)
                    yield self._normalize_stream_chunk(chunk)
                except json.JSONDecodeError:
                    continue
    
    def _normalize_response(self, data: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Normalize provider response to common format."""
        choices = data.get("choices", [])
        if not choices:
            raise LLMProviderError("No choices in response", provider=self.provider_type)
        
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        usage = data.get("usage", {})
        
        return {
            "content": content,
            "model": model,
            "provider": self.provider_type.value,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "finish_reason": choice.get("finish_reason"),
            "request_id": data.get("id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _normalize_stream_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize stream chunk."""
        choices = chunk.get("choices", [])
        if not choices:
            return {"type": "empty"}
        
        choice = choices[0]
        delta = choice.get("delta", {})
        
        return {
            "type": "content",
            "content": delta.get("content", ""),
            "finish_reason": choice.get("finish_reason"),
        }


# =============================================================================
# OPENROUTER PROVIDER
# =============================================================================

class OpenRouterProvider(BaseProvider):
    """OpenRouter provider implementation."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER
    
    @property
    def available_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                model_id="openai/gpt-4o",
                provider=ProviderType.OPENROUTER,
                capabilities=[ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.REASONING],
                max_tokens=4096,
                context_window=128000,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
            ),
            ModelInfo(
                model_id="anthropic/claude-3.5-sonnet",
                provider=ProviderType.OPENROUTER,
                capabilities=[ModelCapability.CHAT, ModelCapability.REASONING, ModelCapability.CODE],
                max_tokens=8192,
                context_window=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
            ),
        ]
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs,
    ) -> Dict[str, Any]:
        # Implementation similar to GroqProvider but with OpenRouter API
        model = self._validate_model(model)
        # ... implementation
        pass
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # ... implementation
        yield {"type": "not_implemented"}


# =============================================================================
# PROVIDER REGISTRY
# =============================================================================

class ProviderRegistry:
    """Central registry for all LLM providers."""
    
    def __init__(self):
        self._providers: Dict[ProviderType, BaseProvider] = {}
        self._default_provider: Optional[ProviderType] = None
        self._model_to_provider: Dict[str, ProviderType] = {}
    
    def register(self, provider: BaseProvider, is_default: bool = False) -> None:
        """Register a provider."""
        if not provider.config.enabled:
            logger.info(f"Provider {provider.provider_type.value} is disabled, skipping")
            return
        
        self._providers[provider.provider_type] = provider
        
        # Update model-to-provider mapping
        for model in provider.available_models:
            self._model_to_provider[model.model_id] = provider.provider_type
        
        if is_default or self._default_provider is None:
            self._default_provider = provider.provider_type
        
        logger.info(f"Registered provider: {provider.provider_type.value} with {len(provider.available_models)} models")
    
    def get_provider(self, provider_type: ProviderType) -> Optional[BaseProvider]:
        """Get provider by type."""
        return self._providers.get(provider_type)
    
    def get_provider_for_model(self, model: str) -> Optional[BaseProvider]:
        """Get provider that supports a model."""
        # Try direct mapping
        if model in self._model_to_provider:
            return self._providers[self._model_to_provider[model]]
        
        # Try resolve via active_models
        from config.active_models import resolve_model_id
        resolved = resolve_model_id(model)
        if resolved in self._model_to_provider:
            return self._providers[self._model_to_provider[resolved]]
        
        # Fall back to default
        if self._default_provider:
            return self._providers[self._default_provider]
        
        return None
    
    def list_providers(self) -> List[ProviderType]:
        return list(self._providers.keys())
    
    def list_models(self, provider_type: Optional[ProviderType] = None) -> List[ModelInfo]:
        if provider_type:
            provider = self._providers.get(provider_type)
            return provider.available_models if provider else []
        models = []
        for provider in self._providers.values():
            models.extend(provider.available_models)
        return models


# =============================================================================
# FALLBACK & RETRY POLICY
# =============================================================================

class FallbackPolicy:
    """Manages fallback and retry behavior."""
    
    def __init__(
        self,
        max_fallback_depth: int = 3,
        fallback_on: Tuple[type, ...] = (LLMProviderError,),
        excluded_error_codes: Tuple[str, ...] = ("auth_error", "model_not_allowed", "quota_exceeded"),
    ):
        self.max_fallback_depth = max_fallback_depth
        self.fallback_on = fallback_on
        self.excluded_error_codes = excluded_error_codes
    
    def should_fallback(self, error: Exception, attempt: int) -> bool:
        """Determine if fallback should be attempted."""
        if attempt >= self.max_fallback_depth:
            return False
        
        if not isinstance(error, self.fallback_on):
            return False
        
        if isinstance(error, LLMProviderError):
            if error.error_code in self.excluded_error_codes:
                return False
            if not error.retryable:
                return False
        
        return True
    
    def get_fallback_model(self, failed_model: str, attempt: int) -> Optional[str]:
        """Get next model to try from fallback chain."""
        from config.active_models import fallback_chain, resolve_model_id
        
        chain = fallback_chain(failed_model)
        if attempt < len(chain):
            return chain[attempt]
        return None


class RetryPolicy:
    """Manages retry behavior with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: float = 0.1,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """Calculate delay before next retry."""
        if retry_after:
            return min(float(retry_after), self.max_delay)
        
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        # Add jitter
        import random
        jitter_range = delay * self.jitter
        delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        
        if isinstance(error, LLMProviderError):
            if not error.retryable:
                return False
            if error.error_code in ("auth_error", "model_not_allowed", "quota_exceeded"):
                return False
        
        return True


# =============================================================================
# PROVIDER MANAGER
# =============================================================================

class ProviderManager:
    """High-level provider management with fallback and retry."""
    
    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        fallback_policy: Optional[FallbackPolicy] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.registry = registry or ProviderRegistry()
        self.fallback_policy = fallback_policy or FallbackPolicy()
        self.retry_policy = retry_policy or RetryPolicy()
        self._cost_tracker: Dict[str, float] = {}  # user_id -> cost
    
    def register_provider(self, provider: BaseProvider, is_default: bool = False) -> None:
        self.registry.register(provider, is_default)
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        provider_type: Optional[ProviderType] = None,
        user_id: Optional[str] = None,
        max_cost_usd: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate completion with automatic fallback and retry.
        
        Args:
            messages: Chat messages
            model: Specific model (optional, uses default chain)
            provider_type: Force specific provider
            user_id: For cost tracking
            max_cost_usd: Maximum cost for this request
            **kwargs: Additional generation parameters
        """
        # Determine model and provider
        if not model:
            from config.active_models import PRIMARY_CHAT_MODEL
            model = PRIMARY_CHAT_MODEL
        
        provider = self.registry.get_provider_for_model(model)
        if not provider:
            if self.registry._default_provider:
                provider = self.registry.get_provider(self.registry._default_provider)
            else:
                raise LLMProviderError("No providers available", status_code=503)
        
        # Override if specific provider requested
        if provider_type:
            specific_provider = self.registry.get_provider(provider_type)
            if specific_provider:
                provider = specific_provider
        
        # Track attempt
        attempt = 0
        current_model = model
        current_provider = provider
        last_error: Optional[Exception] = None
        
        while True:
            try:
                # Check cost budget
                if max_cost_usd and user_id:
                    current_cost = self._cost_tracker.get(user_id, 0.0)
                    if current_cost >= max_cost_usd:
                        raise LLMProviderError(
                            f"Cost budget exceeded: ${current_cost:.4f} >= ${max_cost_usd:.4f}",
                            error_code="budget_exceeded",
                            retryable=False,
                        )
                
                # Execute with retry
                retry_attempt = 0
                while True:
                    try:
                        result = await current_provider.generate(messages, current_model, **kwargs)
                        
                        # Track cost
                        if user_id and "usage" in result:
                            cost = current_provider._estimate_cost(
                                current_model,
                                result["usage"].get("prompt_tokens", 0),
                                result["usage"].get("completion_tokens", 0),
                            )
                            self._cost_tracker[user_id] = self._cost_tracker.get(user_id, 0.0) + cost
                        
                        # Add provider metadata
                        result["_provider"] = current_provider.provider_type.value
                        result["_model"] = current_model
                        result["_attempt"] = attempt
                        return result
                    
                    except LLMProviderError as e:
                        last_error = e
                        
                        # Check retry
                        if self.retry_policy.should_retry(e, retry_attempt):
                            delay = self.retry_policy.calculate_delay(
                                retry_attempt,
                                e.retry_after,
                            )
                            logger.warning(
                                f"Retry {retry_attempt + 1}/{self.retry_policy.max_retries} "
                                f"after {delay:.1f}s for {current_model}: {e}"
                            )
                            await asyncio.sleep(delay)
                            retry_attempt += 1
                            continue
                        
                        # Check fallback
                        if self.fallback_policy.should_fallback(e, attempt):
                            fallback_model = self.fallback_policy.get_fallback_model(current_model, attempt)
                            if fallback_model:
                                current_model = fallback_model
                                current_provider = self.registry.get_provider_for_model(current_model)
                                if not current_provider:
                                    # Try default
                                    current_provider = provider
                                attempt += 1
                                retry_attempt = 0
                                continue
                        
                        # No fallback or retry possible
                        raise
        
        # Should not reach here
        raise last_error or LLMProviderError("All providers exhausted", status_code=503)
    except Exception as e:
        logger.error(f"Unexpected error in provider manager: {e}")
        raise LLMProviderError(f"Provider manager error: {e}", status_code=503) from e
    
    def get_cost(self, user_id: str) -> float:
        """Get accumulated cost for user."""
        return self._cost_tracker.get(user_id, 0.0)
    
    def reset_cost(self, user_id: str) -> None:
        """Reset cost tracking for user."""
        if user_id in self._cost_tracker:
            del self._cost_tracker[user_id]


# =============================================================================
# RESPONSE CONTRACT
# =============================================================================

@dataclass
class GenerationResponse:
    """Standardized generation response."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None
    request_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _provider: Optional[str] = None
    _model: Optional[str] = None
    _attempt: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (excludes internal fields)."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "request_id": self.request_id,
            "created_at": self.created_at,
            "error": self.error,
            "error_code": self.error_code,
        }
    
    @classmethod
    def error_response(
        cls,
        error: str,
        error_code: str,
        model: str = "unknown",
        provider: str = "unknown",
    ) -> "GenerationResponse":
        return cls(
            content="",
            model=model,
            provider=provider,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            error=error,
            error_code=error_code,
        )


# =============================================================================
# COST BUDGET MANAGEMENT
# =============================================================================

class CostBudgetManager:
    """Manages cost budgets per user and globally."""
    
    def __init__(
        self,
        daily_budget_usd: float = 10.0,
        monthly_budget_usd: float = 100.0,
        per_request_limit_usd: float = 1.0,
    ):
        self.daily_budget_usd = daily_budget_usd
        self.monthly_budget_usd = monthly_budget_usd
        self.per_request_limit_usd = per_request_limit_usd
        
        self._daily_spend: Dict[str, float] = {}  # date -> amount
        self._monthly_spend: Dict[str, float] = {}  # month -> amount
        self._user_daily: Dict[str, Dict[str, float]] = {}  # user_id -> date -> amount
        self._user_monthly: Dict[str, Dict[str, float]] = {}  # user_id -> month -> amount
    
    def check_budget(
        self,
        estimated_cost: float,
        user_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if request fits within budget."""
        now = datetime.now(timezone.utc)
        date_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")
        
        # Global daily
        daily_spent = self._daily_spend.get(date_key, 0.0)
        if daily_spent + estimated_cost > self.daily_budget_usd:
            return False, f"Daily budget exceeded (${daily_spent:.2f} / ${self.daily_budget_usd:.2f})"
        
        # Global monthly
        monthly_spent = self._monthly_spend.get(month_key, 0.0)
        if monthly_spent + estimated_cost > self.monthly_budget_usd:
            return False, f"Monthly budget exceeded (${monthly_spent:.2f} / ${self.monthly_budget_usd:.2f})"
        
        # Per-request limit
        if estimated_cost > self.per_request_limit_usd:
            return False, f"Request cost ${estimated_cost:.4f} exceeds per-request limit ${self.per_request_limit_usd:.4f}"
        
        # User-specific
        if user_id:
            user_daily = self._user_daily.get(user_id, {}).get(date_key, 0.0)
            # Could add per-user limits here
        
        return True, None
    
    def record_spend(
        self,
        actual_cost: float,
        user_id: Optional[str] = None,
    ) -> None:
        """Record actual spend after request."""
        now = datetime.now(timezone.utc)
        date_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")
        
        self._daily_spend[date_key] = self._daily_spend.get(date_key, 0.0) + actual_cost
        self._monthly_spend[month_key] = self._monthly_spend.get(month_key, 0.0) + actual_cost
        
        if user_id:
            if user_id not in self._user_daily:
                self._user_daily[user_id] = {}
            self._user_daily[user_id][date_key] = self._user_daily[user_id].get(date_key, 0.0) + actual_cost
            
            if user_id not in self._user_monthly:
                self._user_monthly[user_id] = {}
            self._user_monthly[user_id][month_key] = self._user_monthly[user_id].get(month_key, 0.0) + actual_cost
    
    def get_usage_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics."""
        now = datetime.now(timezone.utc)
        date_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")
        
        stats = {
            "daily_spend": self._daily_spend.get(date_key, 0.0),
            "daily_budget": self.daily_budget_usd,
            "monthly_spend": self._monthly_spend.get(month_key, 0.0),
            "monthly_budget": self.monthly_budget_usd,
        }
        
        if user_id:
            stats["user_daily"] = self._user_daily.get(user_id, {}).get(date_key, 0.0)
            stats["user_monthly"] = self._user_monthly.get(user_id, {}).get(month_key, 0.0)
        
        return stats


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

_provider_registry: Optional[ProviderRegistry] = None
_provider_manager: Optional[ProviderManager] = None
_cost_budget_manager: Optional[CostBudgetManager] = None


def get_provider_registry() -> ProviderRegistry:
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = ProviderRegistry()
        # Register default providers
        groq_config = ProviderConfig(
            provider_type=ProviderType.GROQ,
            api_key_env="GROQ_API_KEY",
            base_url="https://api.groq.com/openai/v1",
            allowed_models=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        )
        _provider_registry.register(GroqProvider(groq_config), is_default=True)
    return _provider_registry


def get_provider_manager() -> ProviderManager:
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager(get_provider_registry())
    return _provider_manager


def get_cost_budget_manager() -> CostBudgetManager:
    global _cost_budget_manager
    if _cost_budget_manager is None:
        _cost_budget_manager = CostBudgetManager(
            daily_budget_usd=float(os.getenv("LLM_DAILY_BUDGET_USD", "50.0")),
            monthly_budget_usd=float(os.getenv("LLM_MONTHLY_BUDGET_USD", "500.0")),
            per_request_limit_usd=float(os.getenv("LLM_PER_REQUEST_LIMIT_USD", "2.0")),
        )
    return _cost_budget_manager


async def generate_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    provider_type: Optional[ProviderType] = None,
    user_id: Optional[str] = None,
    max_cost_usd: Optional[float] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function for generating completions."""
    return await get_provider_manager().generate(
        messages=messages,
        model=model,
        provider_type=provider_type,
        user_id=user_id,
        max_cost_usd=max_cost_usd,
        **kwargs,
    )


__all__ = [
    # Enums
    "ProviderType",
    "ModelCapability",
    
    # Data classes
    "ModelInfo",
    "ProviderConfig",
    "ProviderType",
    "LLMProviderError",
    "GenerationResponse",
    
    # Core classes
    "BaseProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "ProviderRegistry",
    "FallbackPolicy",
    "RetryPolicy",
    "ProviderManager",
    "CostBudgetManager",
    
    # Globals
    "get_provider_registry",
    "get_provider_manager",
    "get_cost_budget_manager",
    "generate_completion",
    
    # Response contract
    "GenerationResponse",
]