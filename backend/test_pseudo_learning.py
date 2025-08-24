"""Tests for pseudo-learning correction storage and retrieval."""

from memory.pseudo_learning import (
    remember_correction,
    retrieve_relevant_corrections,
    forget_correction,
    corrections_collection,
)


def test_store_and_retrieve_correction():
    user = "user_pl"
    corrections_collection.delete_many({"user_id": user})
    r = remember_correction(
        user_id=user,
        original_question="What is 2+2?",
        original_answer="It's 5",
        correction_text="Actually it's 4.",
        tags=["math"],
    )
    assert r["status"] in ("stored", "duplicate")
    # Retrieval (vector may not work in test env; fallback regex)
    res = retrieve_relevant_corrections(user, "2+2")
    assert res, "Should retrieve correction"
    assert any("Actually" in c["correction_text"] for c in res)


def test_forget_correction():
    user = "user_pl2"
    corrections_collection.delete_many({"user_id": user})
    r = remember_correction(
        user_id=user,
        original_question="Capital of France?",
        original_answer="Berlin",
        correction_text="Correction: It's Paris.",
        tags=["geo"],
    )
    h = r.get("hash")
    d = forget_correction(user, h)
    assert d["status"] == "deleted"
