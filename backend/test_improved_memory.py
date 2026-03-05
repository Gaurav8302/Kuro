#!/usr/bin/env python3
"""
Memory System v2 — Integration Tests

Tests the refactored minimal/deterministic memory system:
  - Layer 1: Active session memory (raw messages from MongoDB)
  - Layer 2: Post-session long-term memory (Pinecone summaries)
  - Context builder (system + history + user message)
  - Model locking per session
  - Long-term recall triggers
"""

import uuid
import time

# These imports are safe without API keys
from memory.long_term_memory import should_retrieve_long_term
from memory.model_lock import resolve_model, get_locked_model, lock_model


def test_session_memory():
    """Test Layer 1 — raw message fetch from MongoDB (requires API keys)."""
    from memory.chat_manager_v2 import chat_with_memory
    from memory.user_profile import set_user_name
    from memory.chat_database import create_new_session
    from memory.session_memory import session_memory

    print("🧠 Testing Session Memory (Layer 1)")

    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = create_new_session(test_user_id)
    set_user_name(test_user_id, "TestUser")

    # Conversation 1
    print("\n1. Establishing context…")
    response1 = chat_with_memory(
        test_user_id,
        "My favorite programming language is Python because it's so versatile",
        session_id,
    )
    print(f"Response 1: {response1[:100]}…")

    time.sleep(1)

    # Conversation 2 — should recall Python via raw history
    print("\n2. Testing if model sees previous raw message…")
    response2 = chat_with_memory(
        test_user_id,
        "What programming language did I just mention?",
        session_id,
    )
    print(f"Response 2: {response2[:100]}…")

    # Validate that the raw messages are stored
    msgs = session_memory.get_recent_messages(session_id)
    print(f"\n   → {len(msgs)} messages in session")
    assert len(msgs) >= 4, f"Expected ≥4 messages, got {len(msgs)}"

    memory_indicators = ["python", "programming", "language"]
    if any(ind in response2.lower() for ind in memory_indicators):
        print("✅ Session memory working — referenced Python")
    else:
        print("⚠️  Session memory may not have recalled Python (check model response)")

    return session_id, test_user_id


def test_context_builder():
    """Test context_builder produces correct structure (requires MongoDB)."""
    from memory.chat_database import save_chat_to_db, create_new_session
    from memory.context_builder import build_context

    print("\n🏗️  Testing Context Builder")

    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = create_new_session(test_user_id)

    # Seed a few messages
    save_chat_to_db(test_user_id, "Hello!", "Hi there!", session_id)
    save_chat_to_db(test_user_id, "What is 2+2?", "4", session_id)
    save_chat_to_db(test_user_id, "Thanks!", "You're welcome!", session_id)

    ctx = build_context(
        session_id=session_id,
        user_id=test_user_id,
        new_message="Tell me a joke",
        user_name="TestUser",
    )

    assert "system" in ctx
    assert "messages" in ctx
    assert "debug" in ctx

    msgs = ctx["messages"]
    debug = ctx["debug"]

    # Should have: system + 3 exchanges (6 role messages) + new user msg = 8
    print(f"   → {len(msgs)} messages in context")
    print(f"   → ~{debug['estimated_tokens']} tokens")
    print(f"   → LT triggered: {debug['long_term_triggered']}")

    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == "Tell me a joke"
    assert debug["long_term_triggered"] is False

    print("✅ Context builder structure correct")
    return session_id, test_user_id


def test_long_term_triggers():
    """Test that recall phrases correctly trigger long-term retrieval."""
    print("\n🔍 Testing Long-Term Memory Triggers")

    trigger_cases = [
        ("Do you remember what we talked about last time?", True),
        ("In our previous session you mentioned Python", True),
        ("Remember when I asked about machine learning?", True),
        ("What is the capital of France?", False),
        ("Hello, how are you?", False),
        ("We talked about neural networks earlier", True),
    ]

    passed = 0
    for message, expected in trigger_cases:
        triggered, reason = should_retrieve_long_term(message)
        status = "✅" if triggered == expected else "❌"
        print(f"   {status} '{message[:50]}…' → triggered={triggered} (expected={expected})")
        if triggered == expected:
            passed += 1

    print(f"\n   {passed}/{len(trigger_cases)} trigger tests passed")
    assert passed == len(trigger_cases), f"Some trigger tests failed ({passed}/{len(trigger_cases)})"
    print("✅ All trigger tests passed")


def test_model_locking():
    """Test session-level model locking."""
    print("\n🔒 Testing Model Locking")

    session_id = f"lock_test_{uuid.uuid4().hex[:8]}"

    # First call — should lock to router_pick
    result = resolve_model(session_id, "Hello", "llama-3.3-70b-versatile")
    assert result["model_id"] == "llama-3.3-70b-versatile"
    assert result["source"] == "router_initial"
    print(f"   ✅ Initial lock: {result['model_id']} (source={result['source']})")

    # Second call — same model, normal message
    result2 = resolve_model(session_id, "How are you?", "deepseek-r1-distill-llama-70b")
    assert result2["model_id"] == "llama-3.3-70b-versatile"  # should keep original
    assert result2["source"] == "session_lock"
    print(f"   ✅ Locked reuse: {result2['model_id']} (source={result2['source']})")

    # Explicit code request — should override
    result3 = resolve_model(session_id, "Write code for a Python web scraper", "llama-3.1-8b-instant")
    assert result3["override_reason"] == "explicit_code_request"
    assert result3["model_id"] == "llama-3.1-8b-instant"
    print(f"   ✅ Code override: {result3['model_id']} (reason={result3['override_reason']})")

    print("✅ Model locking tests passed")


def test_context_building_multi_turn():
    """Test context building with 10+ conversation turns (the core bug scenario)."""
    from memory.chat_database import save_chat_to_db, create_new_session
    from memory.context_builder import build_context

    print("\n📝 Testing Multi-Turn Context (Regression)")

    test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = create_new_session(test_user_id)

    conversations = [
        ("I'm planning a trip to Japan", "That sounds exciting! Japan is a wonderful destination."),
        ("I want to visit Tokyo and Kyoto", "Great choices! Tokyo for modern culture, Kyoto for traditions."),
        ("My budget is $3000", "That's a reasonable budget for 10-14 days in Japan."),
        ("I'll be there for 10 days", "Perfect! Here's a rough itinerary for 10 days."),
        ("I love sushi and ramen", "You'll be in heaven! Japan has the best of both."),
        ("I also want to see Mt Fuji", "Mt Fuji is breathtaking. Best viewed from Hakone or Lake Kawaguchi."),
        ("What about the bullet train?", "The Shinkansen is incredible. Get a Japan Rail Pass."),
        ("How much is the JR Pass?", "A 7-day JR Pass costs about $230."),
        ("Can I use it everywhere?", "It covers most JR lines including Shinkansen and some buses."),
        ("What about hotels?", "Budget about $80-150/night. Try ryokans for a traditional experience."),
    ]

    for msg, reply in conversations:
        save_chat_to_db(test_user_id, msg, reply, session_id)

    # Now build context for an 11th message — should have all 10 previous turns
    ctx = build_context(
        session_id=session_id,
        user_id=test_user_id,
        new_message="Summarize everything we've discussed about my trip",
    )

    debug = ctx["debug"]
    msgs = ctx["messages"]

    # We should see all 10 exchanges (20 messages) + system + new user = 22
    non_system = [m for m in msgs if m["role"] != "system"]
    user_msgs = [m for m in non_system if m["role"] == "user"]

    print(f"   → {len(non_system)} non-system messages in context")
    print(f"   → {len(user_msgs)} user messages (incl. new)")
    print(f"   → ~{debug['estimated_tokens']} tokens")

    # The new message is the 11th user message
    assert len(user_msgs) == 11, f"Expected 11 user messages, got {len(user_msgs)}"

    # Verify key topics are present in the context
    full_text = " ".join(m["content"] for m in msgs)
    key_topics = ["Japan", "Tokyo", "Kyoto", "$3000", "10 days", "sushi", "Mt Fuji", "Shinkansen", "JR Pass", "hotels"]
    found = [t for t in key_topics if t.lower() in full_text.lower()]

    print(f"   → {len(found)}/{len(key_topics)} key topics preserved in context")
    assert len(found) == len(key_topics), f"Missing: {set(key_topics) - set(found)}"

    print("✅ Multi-turn context regression test passed (no data loss at turn 5-6)")


def main():
    """Run all memory v2 tests."""
    print("🚀 Memory System v2 — Integration Tests")
    print("=" * 60)

    try:
        # Offline tests (no API keys / MongoDB needed)
        test_long_term_triggers()
        test_model_locking()

        # MongoDB-dependent tests (no LLM API keys needed)
        try:
            test_context_builder()
            test_context_building_multi_turn()
        except Exception as e:
            if "MongoDB" in str(e) or "connection" in str(e).lower() or "ServerSelection" in str(e):
                print(f"\n⚠️  Skipped context builder tests (no MongoDB): {e}")
            else:
                raise

        # Full chat integration test (requires API keys + MongoDB)
        try:
            test_session_memory()
        except Exception as e:
            if "API" in str(e) or "key" in str(e).lower() or "AI model" in str(e):
                print(f"\n⚠️  Skipped live chat test (no API keys): {e}")
            else:
                raise

        print("\n" + "=" * 60)
        print("🎯 All memory v2 tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
