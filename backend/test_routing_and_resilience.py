import os
import pytest

os.environ['DISABLE_MEMORY_INIT'] = '1'

from routing.model_router import route_model
from reliability.circuit_breaker import allow_request, record_failure, get_state, reset
from utils.token_estimator import estimate_tokens, trim_messages


def test_route_model_basic():
    r = route_model("short hi", context_tokens=100, intent=None)
    assert 'model_id' in r and r['model_id']


def test_circuit_breaker_opens():
    model = 'llama-3.3-70B-versatile'
    reset(model)
    for _ in range(6):
        record_failure(model)
    assert get_state(model) == 'open'
    assert not allow_request(model)  # still within reset window


def test_token_trim():
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": "x"*2000} for _ in range(5)
    ]
    trimmed = trim_messages(msgs, max_tokens=500)
    assert len(trimmed) <= len(msgs)
    assert any(m['role']=='system' for m in trimmed)
    assert estimate_tokens(' '.join(m['content'] for m in trimmed)) <= 500 + 50  # allow some slack
