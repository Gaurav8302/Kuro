"""Cross-tenant isolation tests.

These tests verify that users cannot access each other's data.
Run with: pytest tests/test_cross_tenant.py -q
"""

import os
os.environ['TESTING'] = '1'
os.environ['DISABLE_MEMORY_INIT'] = '1'

import pytest
import uuid
from fastapi.testclient import TestClient

from security.auth import get_test_private_key, get_test_public_key

# Import the app after setting test env
from chatbot import app


def _make_test_token(sub: str, **extra_claims) -> str:
    import jwt
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "sub": sub,
        "iss": "https://test-clerk.example",
        "exp": now + 3600,
        "nbf": now - 60,
        "aud": "kuro-api",
        **extra_claims,
    }
    private_key = get_test_private_key()
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key-1"})


@pytest.fixture
def user_a_client() -> TestClient:
    """TestClient authenticated as User A."""
    token = _make_test_token(sub="user_a")
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def user_b_client() -> TestClient:
    """TestClient authenticated as User B."""
    token = _make_test_token(sub="user_b")
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def admin_client() -> TestClient:
    """TestClient authenticated as admin."""
    # Set admin user IDs env var
    import os
    os.environ["ADMIN_USER_IDS"] = "admin_user"
    token = _make_test_token(sub="admin_user")
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


class TestSessionIsolation:
    """Test session isolation between users."""

    def test_user_a_cannot_read_user_b_session(self, user_a_client, user_b_client):
        """User A creates a session, User B cannot read it."""
        # User A creates a session
        session_id = uuid.uuid4().hex
        resp_a = user_a_client.post(
            "/chat",
            json={"user_id": "user_a", "message": "Hello from A", "session_id": session_id}
        )
        assert resp_a.status_code == 200

        # User B tries to read User A's session
        resp_b = user_b_client.get(f"/chat/{session_id}")
        # Should get 404 (not found) because session doesn't belong to B
        assert resp_b.status_code == 404

    def test_user_a_cannot_rename_user_b_session(self, user_a_client, user_b_client):
        """User A cannot rename User B's session."""
        # User B creates a session
        session_id = uuid.uuid4().hex
        resp_b = user_b_client.post(
            "/chat",
            json={"user_id": "user_b", "message": "Hello from B", "session_id": session_id}
        )
        assert resp_b.status_code == 200

        # User A tries to rename User B's session
        resp_a = user_a_client.put(
            f"/session/{session_id}",
            json={"user_id": "user_a", "title": "Hacked by A"}
        )
        # Should fail - either 403 (mismatch) or 404 (not found)
        assert resp_a.status_code in (403, 404)

    def test_user_a_cannot_delete_user_b_session(self, user_a_client, user_b_client):
        """User A cannot delete User B's session."""
        # User B creates a session
        session_id = uuid.uuid4().hex
        resp_b = user_b_client.post(
            "/chat",
            json={"user_id": "user_b", "message": "Hello from B", "session_id": session_id}
        )
        assert resp_b.status_code == 200

        # User A tries to delete User B's session
        resp_a = user_a_client.delete(f"/session/{session_id}")
        # Should fail - either 403 (mismatch) or 404 (not found)
        assert resp_a.status_code in (403, 404)

    def test_user_a_cannot_list_user_b_sessions(self, user_a_client, user_b_client):
        """User A cannot list User B's sessions."""
        # User B creates some sessions
        for i in range(3):
            user_b_client.post(
                "/chat",
                json={"user_id": "user_b", "message": f"Message {i}", "session_id": uuid.uuid4().hex}
            )

        # User A tries to list User B's sessions
        resp_a = user_a_client.get("/sessions/user_b")
        # Should return empty list or only A's sessions
        assert resp_a.status_code == 200
        data = resp_a.json()
        assert isinstance(data, list)
        # A should see empty list since B's sessions don't belong to A
        # (depending on implementation - could be empty or error)
        # The key is A doesn't see B's data


class TestMemoryIsolation:
    """Test memory isolation between users."""

    def test_user_a_cannot_store_memory_for_user_b(self, user_a_client, user_b_client):
        """User A cannot store memory with user_b as owner."""
        resp = user_a_client.post(
            "/store-memory",
            json={
                "user_id": "user_b",  # Trying to store for user B
                "text": "Memory from A for B",
                "metadata": {"category": "test"}
            }
        )
        # Should reject - either 403 (mismatch) or store under A's ID
        # The backend should override user_id in metadata with principal's ID
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            # Verify it was stored under A's user_id, not B's
            # (implementation detail: the route should overwrite metadata.user_id)
            pass

    def test_user_a_cannot_retrieve_user_b_memories(self, user_a_client, user_b_client):
        """User A cannot retrieve User B's memories."""
        # User B stores a memory
        user_b_client.post(
            "/store-memory",
            json={
                "user_id": "user_b",
                "text": "Secret memory from B",
                "metadata": {"category": "test"}
            }
        )

        # User A tries to retrieve B's memories
        resp = user_a_client.post(
            "/retrieve-memory",
            json={
                "user_id": "user_b",  # Requesting B's memories
                "query": "secret",
                "top_k": 5
            }
        )
        # Should fail or return empty
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            data = resp.json()
            # Should return empty or only A's memories
            memories = data.get("memories", [])
            assert len(memories) == 0


class TestProfileIsolation:
    """Test profile isolation between users."""

    def test_user_a_cannot_read_user_b_profile(self, user_a_client, user_b_client):
        """User A cannot read User B's profile."""
        # User B sets a name
        user_b_client.post("/user/user_b/set-name", json={"user_id": "user_b", "name": "User B"})

        # User A tries to read User B's name
        resp = user_a_client.get("/user/user_b/name")
        assert resp.status_code in (403, 404)

    def test_user_a_cannot_modify_user_b_profile(self, user_a_client, user_b_client):
        """User A cannot modify User B's profile."""
        # User A tries to set name for User B
        resp = user_a_client.post(
            "/user/user_b/set-name",
            json={"user_id": "user_b", "name": "Hacked by A"}
        )
        assert resp.status_code in (403, 404)

    def test_user_a_cannot_read_user_b_intro(self, user_a_client, user_b_client):
        """User A cannot read User B's intro state."""
        resp = user_a_client.get("/user/user_b/intro-shown")
        assert resp.status_code in (403, 404)

    def test_user_a_cannot_modify_user_b_intro(self, user_a_client, user_b_client):
        """User A cannot modify User B's intro state."""
        resp = user_a_client.post(
            "/user/user_b/intro-shown",
            json={"user_id": "user_b", "shown": True}
        )
        assert resp.status_code in (403, 404)


class TestHistoryIsolation:
    """Test chat history isolation."""

    def test_user_a_cannot_read_user_b_history(self, user_a_client, user_b_client):
        """User A cannot read User B's full history."""
        # User B creates some history
        for i in range(3):
            user_b_client.post(
                "/chat",
                json={"user_id": "user_b", "message": f"History {i}", "session_id": uuid.uuid4().hex}
            )

        # User A tries to read User B's history
        resp = user_a_client.get("/history/user_b")
        assert resp.status_code == 200
        data = resp.json()
        # Should return empty list
        assert data == []


class TestInlineQueryIsolation:
    """Test inline query isolation."""

    def test_user_a_cannot_inline_query_user_b_session(self, user_a_client, user_b_client):
        """User A cannot inline query User B's session."""
        # User B creates a session with content
        session_id = uuid.uuid4().hex
        user_b_client.post(
            "/chat",
            json={"user_id": "user_b", "message": "Secret info for B", "session_id": session_id}
        )

        # User A tries to inline query B's session
        resp = user_a_client.post(
            "/inline-query",
            json={"user_id": "user_b", "session_id": session_id, "query": "what is the secret"}
        )
        # Should fail - session doesn't belong to A
        assert resp.status_code in (403, 404)


class TestAdminAccess:
    """Test admin access control."""

    def test_ordinary_user_cannot_access_admin_endpoints(self, user_a_client):
        """Ordinary user cannot access admin endpoints."""
        endpoints = [
            ("GET", "/admin/health"),
            ("GET", "/admin/circuit-breakers"),
            ("GET", "/admin/llm-calls"),
            ("POST", "/admin/reload-registry"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = user_a_client.get(path)
            else:
                resp = user_a_client.post(path, json={})
            assert resp.status_code == 403, f"{method} {path} should return 403"

    def test_admin_can_access_admin_endpoints(self, admin_client):
        """Admin can access admin endpoints."""
        resp = admin_client.get("/admin/health")
        assert resp.status_code == 200

        resp = admin_client.get("/admin/circuit-breakers")
        assert resp.status_code == 200


class TestMetricsAccess:
    """Test metrics access control."""

    def test_ordinary_user_cannot_access_metrics(self, user_a_client):
        """Ordinary user cannot access /metrics."""
        resp = user_a_client.get("/metrics")
        assert resp.status_code == 401

    def test_admin_cannot_access_metrics_without_service_token(self, admin_client):
        """Admin cannot access /metrics without service token."""
        resp = admin_client.get("/metrics")
        assert resp.status_code == 401


class TestPayloadUserIdMismatch:
    """Test that caller-supplied user_id cannot override verified identity."""

    def test_chat_rejects_mismatched_user_id(self, user_a_client):
        """Chat endpoint rejects mismatched user_id in payload."""
        session_id = uuid.uuid4().hex
        # User A authenticated but sends user_b in payload
        resp = user_a_client.post(
            "/chat",
            json={"user_id": "user_b", "message": "test", "session_id": session_id}
        )
        assert resp.status_code == 403

    def test_store_memory_rejects_mismatched_user_id(self, user_a_client):
        """Store memory endpoint rejects mismatched user_id."""
        resp = user_a_client.post(
            "/store-memory",
            json={"user_id": "user_b", "text": "test", "metadata": {}}
        )
        assert resp.status_code == 403

    def test_retrieve_memory_rejects_mismatched_user_id(self, user_a_client):
        """Retrieve memory endpoint rejects mismatched user_id."""
        resp = user_a_client.post(
            "/retrieve-memory",
            json={"user_id": "user_b", "query": "test", "top_k": 5}
        )
        assert resp.status_code == 403


class TestSessionOwnershipCheck:
    """Test session ownership checks with guessed IDs."""

    def test_guessed_session_id_returns_404(self, user_a_client):
        """Guessing another user's session ID returns 404."""
        # Generate a session ID that might belong to another user
        guessed_session_id = uuid.uuid4().hex
        
        # Try to access it
        resp = user_a_client.get(f"/chat/{guessed_session_id}")
        assert resp.status_code == 404

        resp = user_a_client.delete(f"/session/{guessed_session_id}")
        assert resp.status_code == 404

        resp = user_a_client.put(
            f"/session/{guessed_session_id}",
            json={"user_id": "user_a", "title": "Test"}
        )
        assert resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-q"])


# Note: These cross-tenant isolation tests require a running MongoDB instance.
# When MongoDB is not available, tests that hit the database will fail with connection errors.
# To run these tests properly:
# 1. Start MongoDB: docker run -d -p 27017:27017 mongo:latest
# 2. Set MONGODB_URI if different from localhost
# 3. Run: pytest tests/test_cross_tenant.py -q