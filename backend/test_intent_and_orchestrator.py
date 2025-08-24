import os
import pytest
os.environ['DISABLE_MEMORY_INIT'] = '1'

from routing.intent_classifier import classify_intent
from orchestration.llm_orchestrator import orchestrate


def test_intent_classifier_basic():
    assert 'casual_chat' in classify_intent('hello there')
    intents = classify_intent('Please summarise this long document for me')
    assert 'long_context_summary' in intents
    intents2 = classify_intent('Prove the theorem step by step')
    assert 'complex_reasoning' in intents2


@pytest.mark.asyncio
async def test_orchestrator_handles_fallback(monkeypatch):
    # Force a fake failure on first model by monkeypatching GroqClient.generate_content
    from orchestration import llm_orchestrator
    calls = {'n':0}
    real_generate = llm_orchestrator.client.generate_content
    def fake_generate(*a, **kw):
        calls['n'] += 1
        if calls['n'] == 1:
            raise Exception('Simulated failure')
        return 'fallback reply'
    monkeypatch.setattr(llm_orchestrator.client, 'generate_content', fake_generate)
    result = await orchestrate('summarise this text please')
    assert result['reply'] == 'fallback reply'
    assert len(result['fallbacks_used']) >= 1
