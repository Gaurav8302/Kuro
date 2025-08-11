"""Unit tests for rolling memory summarization system.

These tests avoid external LLM calls by injecting a DummySummarizer.
"""

from memory.rolling_memory import RollingMemoryManager


class DummySummarizer:
    def summarize(self, prompt: str) -> str:
        # Deterministic pseudo-summary: count user lines & first 3 words
        lines = [l for l in prompt.splitlines() if l.startswith("User:")]
        bullets = []
        for l in lines:
            words = l.split()[1:4]
            bullets.append("- " + " ".join(words))
        return "FACTS:\n" + "\n".join(bullets[:5]) + "\nOTHER_NOTES:\n- dummy"


def _insert_dummy_messages(chat_db, session_id: str, user_id: str, count: int):
    from datetime import datetime
    chat_db.chat_collection.delete_many({"session_id": session_id})
    for i in range(count):
        chat_db.chat_collection.insert_one(
            {
                "user_id": user_id,
                "session_id": session_id,
                "message": f"Message {i}",
                "reply": f"Reply {i}",
                "timestamp": datetime.utcnow(),
                "metadata": {
                    "sequence_number": i + 1,
                },
            }
        )


def test_progressive_summarization_basic():
    from memory.chat_database import chat_db
    from database.db import conversation_summaries_collection
    session_id = "test_session_progressive"
    user_id = "user_prog"
    conversation_summaries_collection.delete_many({"session_id": session_id})

    mgr = RollingMemoryManager(short_term_window=5, min_chunk=4, summarizer=DummySummarizer())
    _insert_dummy_messages(chat_db, session_id, user_id, 20)

    # Trigger summarization manually
    mgr._maybe_summarize_session(user_id, session_id)  # noqa

    summaries = list(conversation_summaries_collection.find({"session_id": session_id}))
    assert summaries, "No summaries created"
    # Ensure summarized range excludes last short-term_window messages
    max_sequence = max(s["sequence_end"] for s in summaries)
    assert max_sequence <= 15, "Short-term messages should not be summarized"


def test_context_building_and_dedup():
    from memory.chat_database import chat_db
    from database.db import conversation_summaries_collection
    session_id = "test_session_context"
    user_id = "user_ctx"
    conversation_summaries_collection.delete_many({"session_id": session_id})

    mgr = RollingMemoryManager(short_term_window=5, min_chunk=3, summarizer=DummySummarizer())
    _insert_dummy_messages(chat_db, session_id, user_id, 14)
    mgr._maybe_summarize_session(user_id, session_id)  # noqa

    ctx = mgr.build_memory_context(user_id, session_id, "Hello")
    assert "short_term" in ctx and ctx["short_term"], "Short-term missing"
    assert "long_term_summaries" in ctx, "Summaries missing"
    # Dedup ensures no duplicate lines across summaries
    all_lines = []
    for s in ctx["long_term_summaries"]:
        all_lines.extend([l for l in s.splitlines() if l.startswith("-")])
    assert len(all_lines) == len(set(all_lines)), "Duplicate summary lines detected"
