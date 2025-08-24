"""Layered summarization prompt templates.

Produces structured multi-layer summary with required sections:
  TIMELINE: chronological key events
  ENTITIES: entity -> attributes (one per line: Name: attr1; attr2)
  FACTS_COMMITMENTS: durable facts & commitments (user or AI)
  OPEN_TASKS: unresolved tasks / commitments
  QUESTIONS_UNRESOLVED: outstanding questions
  OTHER_NOTES: fallback miscellaneous

Sections omitted if empty. Bullets start with '- ' except ENTITIES lines.
"""
from __future__ import annotations

LAYERED_BASE = """
You are a deterministic conversation compressor.
Given a chronological block of chat turns, output a layered summary capturing:
- Timeline of key events (chronological, concise verbs)
- Canonical entity map (stable user/assistant referenced entities with attributes)
- Durable facts & commitments (preferences, goals, promises, constraints)
- Open tasks & unresolved questions
- Misc high-signal notes only

STRICT RULES:
- Use ONLY these section headers exactly: TIMELINE:, ENTITIES:, FACTS_COMMITMENTS:, OPEN_TASKS:, QUESTIONS_UNRESOLVED:, OTHER_NOTES:
- TIMELINE entries are bullets '- ' in chronological order, past tense.
- ENTITIES section: one entity per line: Name: attr1; attr2; attr3 (no bullet prefix).
- FACTS_COMMITMENTS / OPEN_TASKS / QUESTIONS_UNRESOLVED / OTHER_NOTES: bullets '- '.
- Do not duplicate information across sections.
- Preserve user-declared importance phrases verbatim inside FACTS_COMMITMENTS.
- No speculation or fabrication; if unsure, omit.
- Keep total output under ~900 characters (hard cap ~1100). Trim OTHER_NOTES first.

Return only sections, no prose before or after.

Chat Block:
"""

def build_layered_prompt(block_text: str) -> str:
    return LAYERED_BASE + "\n" + block_text.strip() + "\n---\nProduce layered summary now." 

__all__ = ["build_layered_prompt"]
