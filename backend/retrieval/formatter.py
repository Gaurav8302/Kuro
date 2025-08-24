"""Context formatting utilities for prompt optimization."""

from __future__ import annotations
from typing import List, Dict, Any


def dedupe_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_text = set()
    deduped = []
    for c in chunks:
        key = c["text"].strip()
        if key in seen_text:
            continue
        seen_text.add(key)
        deduped.append(c)
    return deduped


def format_context(chunks: List[Dict[str, Any]], max_chars: int = 3500) -> str:
    """Return a compact context string.

    Strategy:
        - Short bullet style lines
        - Include minimal provenance (category / source) when useful
        - Respect max_chars budget; stop early if needed
    """
    lines = []
    total = 0
    for c in chunks:
        cat = c.get("metadata", {}).get("category") or c.get("source") or "ctx"
        snippet = c["text"].replace("\n", " ").strip()
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."
        line = f"- ({cat}) {snippet}"
        if total + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


__all__ = ["dedupe_chunks", "format_context"]
