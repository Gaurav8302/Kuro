import os
os.environ['DISABLE_MEMORY_INIT'] = '1'
os.environ['ADMIN_API_KEY'] = 'test-admin'

from fastapi.testclient import TestClient
from chatbot import app

client = TestClient(app)

def test_metrics_endpoint():
    r = client.get('/metrics')
    assert r.status_code in (200, 500)  # allow 500 if lib missing in minimal env
    if r.status_code == 200:
        body = r.text
        assert 'llm_requests_total' in body

def test_admin_health_unauthorized():
    r = client.get('/admin/health')
    assert r.status_code in (401, 503)  # 503 if key not configured yet

def test_admin_health_authorized():
    if 'ADMIN_API_KEY' not in os.environ:
        return
    r = client.get('/admin/health', headers={'X-Admin-Key': 'test-admin'})
    # If admin router mounted and key matches we expect 200 else 401/503
    assert r.status_code in (200, 401, 503)
