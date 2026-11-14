"""Regression tests for Maintenance Audit One.

Covers:
- active model selection / legacy remapping
- primary → fallback chain
- provider failure raises (not fake assistant text)
- failed responses are not persisted
- embedding dimension validation
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DISABLE_MEMORY_INIT", "1")
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("GROQ_API_KEY", "test-key-not-real")


def test_active_models_are_current_groq_ids():
    from config.active_models import (
        FALLBACK_CHAT_MODEL,
        PRIMARY_CHAT_MODEL,
        fallback_chain,
        resolve_model_id,
    )

    assert PRIMARY_CHAT_MODEL == "openai/gpt-oss-120b"
    assert FALLBACK_CHAT_MODEL == "openai/gpt-oss-20b"
    assert fallback_chain() == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert resolve_model_id("llama-3.1-8b-instant") == FALLBACK_CHAT_MODEL
    assert resolve_model_id("llama-3.3-70b-versatile") == PRIMARY_CHAT_MODEL
    assert resolve_model_id("deepseek-r1-distill-llama-70b") == PRIMARY_CHAT_MODEL


def test_llm_router_uses_active_models():
    from config.active_models import FALLBACK_CHAT_MODEL, PRIMARY_CHAT_MODEL
    from llm.router import LLMRouter

    router = LLMRouter()
    assert router.get_primary_model_id() == PRIMARY_CHAT_MODEL
    assert router.get_fallback_model_id() == FALLBACK_CHAT_MODEL
    assert router.get_model("conversation").model_name == PRIMARY_CHAT_MODEL
    assert router.get_model("fast").model_name == FALLBACK_CHAT_MODEL
    assert router.get_model("code").model_name == FALLBACK_CHAT_MODEL


def test_generic_model_raises_provider_error_on_failure():
    from llm.errors import LLMProviderError
    from llm.router import GenericModel

    model = GenericModel("openai/gpt-oss-120b")
    mock_client = MagicMock()
    mock_client.generate_content.side_effect = Exception("boom")
    model.client = mock_client

    with pytest.raises(LLMProviderError):
        import asyncio

        asyncio.run(model.generate("hello"))


def test_generic_model_rejects_empty_response():
    from llm.errors import LLMProviderError
    from llm.router import GenericModel

    model = GenericModel("openai/gpt-oss-20b")
    mock_client = MagicMock()
    mock_client.generate_content.return_value = "   "
    model.client = mock_client

    with pytest.raises(LLMProviderError):
        import asyncio

        asyncio.run(model.generate("hello"))


def test_groq_client_tries_fallback_then_raises():
    from llm.errors import LLMProviderError
    from utils.groq_client import GroqClient

    client = GroqClient.__new__(GroqClient)
    client.api_key = "test"
    client.base_url = "https://api.groq.com/openai/v1"
    client.default_params = {"temperature": 0.7, "max_tokens": 64, "top_p": 1, "stream": False}
    client.model = "openai/gpt-oss-120b"

    attempts = []

    def _fail(model, messages, params):
        attempts.append(model)
        raise LLMProviderError(f"fail:{model}", model=model, status_code=404)

    client._call_api = _fail  # type: ignore

    with patch("utils.groq_client.allow_request", return_value=True), patch(
        "utils.groq_client.record_failure"
    ), patch("utils.groq_client.record_success"):
        with pytest.raises(LLMProviderError):
            client.generate_content("hi", model_id="openai/gpt-oss-120b")

    assert attempts == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def test_groq_client_fallback_success():
    from utils.groq_client import GroqClient

    client = GroqClient.__new__(GroqClient)
    client.api_key = "test"
    client.base_url = "https://api.groq.com/openai/v1"
    client.default_params = {"temperature": 0.7, "max_tokens": 64, "top_p": 1, "stream": False}
    client.model = "openai/gpt-oss-120b"

    def _call(model, messages, params):
        if model == "openai/gpt-oss-120b":
            from llm.errors import LLMProviderError

            raise LLMProviderError("primary down", model=model, status_code=404)
        return {"choices": [{"message": {"content": "fallback ok"}}]}

    client._call_api = _call  # type: ignore

    with patch("utils.groq_client.allow_request", return_value=True), patch(
        "utils.groq_client.record_failure"
    ), patch("utils.groq_client.record_success"):
        text = client.generate_content("hi", model_id="openai/gpt-oss-120b")
    assert text == "fallback ok"


def test_chat_endpoint_does_not_persist_on_provider_failure(auth_client):
    os.environ["DISABLE_MEMORY_INIT"] = "1"
    os.environ["TESTING"] = "1"

    from fastapi.testclient import TestClient
    from llm.errors import LLMProviderError

    import chatbot as chatbot_mod

    saved = []

    async def boom(**kwargs):
        raise LLMProviderError("simulated", model="openai/gpt-oss-120b", status_code=502)

    with patch.object(chatbot_mod, "chat_manager_v3_instance") as mgr, patch.object(
        chatbot_mod, "save_chat_to_db", side_effect=lambda **kw: saved.append(kw) or "sess"
    ), patch.object(chatbot_mod, "get_chat_by_session", return_value=[]):
        mgr.handle_chat = boom
        # Force non-legacy path
        with patch.dict(os.environ, {"DISABLE_MEMORY_INIT": "0"}):
            # Mock session ownership check to avoid database calls
            import memory.chat_database as chat_db_mod
            def fake_session_belongs_to_user(session_id, user_id):
                return True
            with patch.object(chat_db_mod.chat_db, "session_belongs_to_user", fake_session_belongs_to_user):
                resp = auth_client.post(
                    "/chat",
                    json={
                        "user_id": "test_user",
                        "message": "hello",
                        "session_id": "sess_test",
                    },
                )

    assert resp.status_code == 502
    body = resp.json()
    assert body.get("error") == "llm_provider_error"
    assert "message" in body
    assert saved == []


def test_embedding_dimension_validation():
    from config.embeddings import EMBEDDING_DIMENSION, validate_embedding_dimension

    ok = [0.1] * EMBEDDING_DIMENSION
    assert len(validate_embedding_dimension(ok)) == EMBEDDING_DIMENSION
    with pytest.raises(ValueError):
        validate_embedding_dimension([0.1] * 384)


def test_normalize_embedding_rejects_zero_vector():
    from config.embeddings import normalize_embedding

    with pytest.raises(ValueError):
        normalize_embedding([0.0] * 768)


def test_no_live_retired_model_defaults():
    from config.active_models import FALLBACK_CHAT_MODEL, PRIMARY_CHAT_MODEL, ROLE_MODELS
    from config.embeddings import EMBEDDING_MODEL

    retired = {
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32k",
        "text-embedding-004",
        "models/text-embedding-004",
    }
    assert PRIMARY_CHAT_MODEL not in retired
    assert FALLBACK_CHAT_MODEL not in retired
    assert EMBEDDING_MODEL not in retired
    for role, mid in ROLE_MODELS.items():
        assert mid not in retired, role
