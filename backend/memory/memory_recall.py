"""
Memory recall utilities for vague recall requests.

Provides functions to fetch fallback profile + summaries when a memory trigger is detected.

Contract:
    build_recall_context(user_id: str, session_id: str | None, manager) -> dict
Returns dict with:
    profile: dict | None
    summaries: list[str]
    short_term: list[dict]
    context_text: str  # formatted for LLM
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple

from memory.user_profile import get_user_profile, get_user_name
from memory.rolling_memory import rolling_memory_manager
from memory.ultra_lightweight_memory import get_relevant_memories_detailed


def _format_recall_context(profile: Optional[dict], summaries: List[str], short_term: List[dict]) -> str:
    parts: List[str] = []
    if profile:
        name = profile.get("name") or "(unknown)"
        # Select a few key fields if present
        keys = [k for k in ["name", "email", "role", "preferences", "goals"] if k in profile]
        lines = [f"- {k}: {profile[k]}" for k in keys]
        parts.append("PROFILE:\n" + ("\n".join(lines) or f"- name: {name}"))
    if summaries:
        parts.append("PAST_SUMMARIES:\n" + "\n---\n".join(summaries[:4]))
    if short_term:
        st_lines = []
        for turn in short_term[-4:]:
            st_lines.append(f"User: {turn['user']}\nAssistant: {turn['assistant']}")
        parts.append("RECENT_TURNS:\n" + "\n\n".join(st_lines))
    return "\n\n".join(parts)


def build_recall_context(user_id: str, session_id: Optional[str] = None, summaries_k: int = 4) -> Dict[str, Any]:
    # Profile from Mongo
    profile = get_user_profile(user_id) or {}
    if not profile:
        # try name-only helper
        nm = get_user_name(user_id)
        if nm:
            profile = {"name": nm}

    # Layered summaries: prefer long-term summaries via rolling memory collection (Mongo-backed) but we can also query vector store as fallback
    summaries: List[str] = []
    try:
        rm = rolling_memory_manager.get_relevant_summaries(user_id, session_id, limit=summaries_k)
        summaries = [s.get("summary", "").strip() for s in rm if s.get("summary")]
    except Exception:
        pass
    if not summaries:
        try:
            # get top-k memories tagged as summaries from vector store
            mems = get_relevant_memories_detailed("session summary layered", user_filter=user_id, top_k=summaries_k)
            for m in mems:
                tx = m.get("text", "")
                if "summary" in m.get("category", "").lower() or "fact" in tx.lower() or "summary" in tx.lower():
                    summaries.append(tx)
        except Exception:
            pass

    # Short-term turns
    short_term: List[dict] = []
    try:
        if session_id:
            short_term = rolling_memory_manager.get_short_term_messages(session_id)
    except Exception:
        pass

    context_text = _format_recall_context(profile or None, summaries, short_term)
    return {
        "profile": profile or None,
        "summaries": summaries,
        "short_term": short_term,
        "context_text": context_text,
    }


__all__ = ["build_recall_context"]
