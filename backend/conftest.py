import os
import sys
import asyncio
import inspect

# Set test mode BEFORE importing chatbot
os.environ['TESTING'] = '1'
os.environ['DISABLE_MEMORY_INIT'] = '1'

# Ensure the backend folder itself is on sys.path so imports like `routing.*` and `chatbot` work in tests
BACKEND_DIR = os.path.dirname(__file__)
sys.path.insert(0, BACKEND_DIR)


def pytest_configure(config):
	# Register marker so pytest doesn't warn when plugin is unavailable.
	config.addinivalue_line("markers", "asyncio: mark test as asyncio coroutine")


def pytest_pyfunc_call(pyfuncitem):
	"""Run async tests via asyncio when pytest-asyncio is not installed."""
	test_func = pyfuncitem.obj
	if not inspect.iscoroutinefunction(test_func):
		return None

	kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
	asyncio.run(test_func(**kwargs))
	return True

# Use the fixed test key pair from auth module
import jwt
from datetime import datetime, timezone

import security.auth
_test_private_key = security.auth.get_test_private_key()
_test_public_key = security.auth.get_test_public_key()

# Now import chatbot (which will also import security.auth, but it's already patched)
from chatbot import app

def _make_test_token(sub: str = "test_user", **extra_claims) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "sub": sub,
        "iss": "https://test-clerk.example",
        "exp": now + 3600,
        "nbf": now - 60,
        "aud": "kuro-api",
        **extra_claims,
    }
    return jwt.encode(claims, _test_private_key, algorithm="RS256", headers={"kid": "test-key-1"})

# Pytest fixture for an authenticated client
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def auth_client() -> TestClient:
    """TestClient with a valid Clerk JWT for a test user."""
    token = _make_test_token()
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})

@pytest.fixture
def admin_client() -> TestClient:
    """TestClient authenticated as an admin user."""
    token = _make_test_token(sub="admin_user")
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})

@pytest.fixture
def other_user_client() -> TestClient:
    """TestClient authenticated as a different user."""
    token = _make_test_token(sub="other_user")
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})

# Make the base app available without auth for public endpoints
@pytest.fixture
def client() -> TestClient:
    return TestClient(app)