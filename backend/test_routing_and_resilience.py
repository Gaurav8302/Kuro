import os
import pytest

os.environ['DISABLE_MEMORY_INIT'] = '1'

from routing.model_router import route_model
from reliability.circuit_breaker import allow_request, record_failure, get_state, reset
from utils.token_estimator import estimate_tokens, trim_messages
from config.model_config import normalize_model_id, KIMMI_CONVERSATIONAL


def test_route_model_basic():
    """Test basic model routing returns a valid model."""
    from config.active_models import FALLBACK_CHAT_MODEL, PRIMARY_CHAT_MODEL

    r = route_model("short hi", context_tokens=100, intent=None)
    assert 'model_id' in r and r['model_id']
    normalized = normalize_model_id(r['model_id'])
    assert normalized in [PRIMARY_CHAT_MODEL, FALLBACK_CHAT_MODEL]


def test_route_model_conversation():
    """Test routing for conversational queries."""
    from config.active_models import FALLBACK_CHAT_MODEL, PRIMARY_CHAT_MODEL

    r = route_model("hello, how are you?", context_tokens=50, intent="casual_chat")
    assert 'model_id' in r
    normalized = normalize_model_id(r['model_id'])
    # Short casual messages may hit either the conversation or short-query rule.
    assert normalized in {PRIMARY_CHAT_MODEL, FALLBACK_CHAT_MODEL, normalize_model_id(KIMMI_CONVERSATIONAL)}


def test_circuit_breaker_opens():
    """Test circuit breaker opens after repeated failures."""
    from config.active_models import PRIMARY_CHAT_MODEL

    model = normalize_model_id(PRIMARY_CHAT_MODEL)
    reset(model)
    for _ in range(6):
        record_failure(model)
    assert get_state(model) == 'open'
    assert not allow_request(model)  # still within reset window


def test_token_trim():
    """Test token trimming preserves system messages."""
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": "x"*2000} for _ in range(5)
    ]
    trimmed = trim_messages(msgs, max_tokens=500)
    assert len(trimmed) <= len(msgs)
    assert any(m['role']=='system' for m in trimmed)
    assert estimate_tokens(' '.join(m['content'] for m in trimmed)) <= 500 + 50  # allow some slack
