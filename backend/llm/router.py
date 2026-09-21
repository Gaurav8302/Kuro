"""Live LLM router for ChatManagerV3.

Uses the central active_models configuration:
  primary  -> openai/gpt-oss-120b
  fallback -> openai/gpt-oss-20b

Provider failures raise LLMProviderError. Callers must not treat those as
successful assistant replies.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from config.active_models import (
    FALLBACK_CHAT_MODEL,
    PRIMARY_CHAT_MODEL,
    fallback_chain,
    get_role_model,
    resolve_model_id,
)
from llm.errors import LLMProviderError

logger = logging.getLogger(__name__)


class GenericModel:
    def __init__(self, model_name: str):
        self.model_name = resolve_model_id(model_name)
        self.client = None
        try:
            from utils.groq_client import GroqClient

            self.client = GroqClient()
        except Exception as exc:
            logger.error("Failed to initialize GroqClient: %s", exc)
            self.client = None

    async def generate(self, prompt: str) -> str:
        if not self.client:
            raise LLMProviderError(
                "Groq client is not configured (missing GROQ_API_KEY?)",
                model=self.model_name,
                status_code=503,
            )

        try:
            text = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                model_id=self.model_name,
            )
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error("Error generating from model %s: %s", self.model_name, exc)
            raise LLMProviderError(
                str(exc),
                model=self.model_name,
                status_code=502,
            ) from exc

        if text is None or not str(text).strip():
            raise LLMProviderError(
                "Provider returned an empty response",
                model=self.model_name,
                status_code=502,
            )
        return str(text).strip()


class FastModel(GenericModel):
    def __init__(self):
        super().__init__(get_role_model("fast"))


class MidModel(GenericModel):
    def __init__(self):
        super().__init__(get_role_model("mid"))


class MainModel(GenericModel):
    def __init__(self):
        super().__init__(get_role_model("main"))


class LLMRouter:
    def get_model(self, model_type: str):
        role = model_type if model_type in {
            "fast", "mid", "main", "conversation", "code", "reasoning", "summarization"
        } else "main"
        return GenericModel(get_role_model(role))

    def get_primary_model_id(self) -> str:
        return PRIMARY_CHAT_MODEL

    def get_fallback_model_id(self) -> str:
        return FALLBACK_CHAT_MODEL

    def get_attempt_chain(self, primary: Optional[str] = None):
        return fallback_chain(primary)
