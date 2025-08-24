import pytest
from memory.context_rehydrator import build_context


def test_build_context_empty():
    context, meta = build_context(user_id="u-none", session_id="s-none", current_query="orphan", max_tokens=200)
    # Should gracefully return something (may be empty if no memory)
    assert isinstance(context, str)
    assert 'FACTS' not in context  # no facts expected
    assert meta['summary_count'] >= 0


def test_token_budget_trimming(monkeypatch):
    # Monkeypatch token estimator to force trimming
    from utils import token_estimator
    def huge(_):
        return 10_000
    monkeypatch.setattr(token_estimator, 'estimate_tokens', huge)
    context, _ = build_context(user_id="u-none", session_id="s-none", current_query="overflow", max_tokens=50)
    # With huge token count we progressively drop summaries; final still string
    assert isinstance(context, str)

