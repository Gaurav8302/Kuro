import os
os.environ['LOG_RAW_CONTENT'] = 'false'
os.environ['DISABLE_MEMORY_INIT'] = '1'

import asyncio
import json
from fastapi.testclient import TestClient
from chatbot import app

client = TestClient(app)

def test_request_id_header_present():
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'X-Request-ID' in resp.headers
    assert len(resp.headers['X-Request-ID']) > 10

# Basic test to ensure middleware doesn't break chat route (mock minimal payload)
def test_chat_route_instrumented(monkeypatch):
    # Monkeypatch chat_with_memory to avoid heavy dependencies
    from memory import chat_manager
    def fake_chat_with_memory(user_id, message, session_id=None):
        return 'ok'
    monkeypatch.setattr(chat_manager, 'chat_with_memory', fake_chat_with_memory)

    payload = {"user_id": "u1", "message": "hi"}
    resp = client.post('/chat', json=payload)
    assert resp.status_code == 200
    assert 'X-Request-ID' in resp.headers
    data = resp.json()
    assert 'reply' in data and data['reply'] == 'ok'
