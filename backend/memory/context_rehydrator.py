"""Context rehydration utilities.

Builds prompt context from:
 - Short-term raw turns
 - Retrieved layered summaries (semantic)
 - Verbatim facts (high importance)
Implements deduplication & token budget trimming.
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple
from memory.rolling_memory import rolling_memory_manager
from memory.ultra_lightweight_memory import get_relevant_memories_detailed
from utils.token_estimator import estimate_tokens


def build_context(user_id: str, session_id: str, current_query: str, max_tokens: int = 2000) -> Tuple[str, Dict[str, Any]]:
    rm_ctx = rolling_memory_manager.build_memory_context(user_id, session_id, current_query)
    short_term = rm_ctx.get('short_term', [])
    # Semantic retrieve top layered summaries & verbatim facts
    semantic = get_relevant_memories_detailed(current_query, user_filter=user_id, top_k=8)
    layered_chunks = [m['text'] for m in semantic if m.get('category') == 'summary' or 'layered' in m.get('text','').lower()]
    facts = [m['text'] for m in semantic if 'fact' in m.get('text','').lower()][:15]
    # Deduplicate facts
    seen = set()
    dedup_facts = []
    for f in facts:
        k = f.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup_facts.append(f)
    # Assemble sections with priority: facts -> summaries -> recent turns
    parts: List[str] = []
    if dedup_facts:
        parts.append("FACTS:\n" + "\n".join(dedup_facts))
    if layered_chunks:
        parts.append("SUMMARIES:\n" + "\n---\n".join(layered_chunks[:5]))
    if short_term:
        st_lines = []
        for turn in short_term:
            st_lines.append(f"User: {turn['user']}\nAssistant: {turn['assistant']}")
        parts.append("RECENT_TURNS:\n" + "\n\n".join(st_lines))
    context = "\n\n".join(parts)
    # Token budget trimming (simple heuristic: drop earliest summaries then truncate recent turns)
    while estimate_tokens(context) > max_tokens and layered_chunks:
        layered_chunks.pop(0)
        rebuild = []
        if dedup_facts:
            rebuild.append("FACTS:\n" + "\n".join(dedup_facts))
        if layered_chunks:
            rebuild.append("SUMMARIES:\n" + "\n---\n".join(layered_chunks))
        if short_term:
            st_lines = []
            for turn in short_term:
                st_lines.append(f"User: {turn['user']}\nAssistant: {turn['assistant']}")
            rebuild.append("RECENT_TURNS:\n" + "\n\n".join(st_lines))
        context = "\n\n".join(rebuild)
    return context, {"facts": dedup_facts, "summary_count": len(layered_chunks), "short_term_count": len(short_term)}

__all__ = ["build_context"]
