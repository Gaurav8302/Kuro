"""
Context Assembler — Token-Aware Prompt Construction

Assembles the final prompt payload with intelligent token budgeting.
Ensures that memories, history, and system prompt fit within the
model's context window without truncating critical information.

Token estimation uses the standard approximation:
  tokens ≈ len(text) / 4  (for English text)
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Approximate tokens per character (English text average)
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


class ContextAssembler:
    """Token-aware prompt assembly with dynamic budget allocation."""

    def __init__(
        self,
        default_budget: int = 28000,
        response_headroom: int = 2000,
        memory_ratio: float = 0.15,
        history_ratio: float = 0.65,
    ):
        """
        Args:
            default_budget: Total token budget for the assembled prompt.
            response_headroom: Tokens reserved for the model's response.
            memory_ratio: Fraction of remaining budget for memories.
            history_ratio: Fraction of remaining budget for chat history.
        """
        self.default_budget = default_budget
        self.response_headroom = response_headroom
        self.memory_ratio = memory_ratio
        self.history_ratio = history_ratio

    def build(
        self,
        system_prompt: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, str]],
        user_message: str,
        style_hint: str = "",
        token_budget: Optional[int] = None,
    ) -> str:
        """Assemble the final prompt with token budgeting.

        Priority order (what gets cut first):
        1. Older history messages (oldest removed first)
        2. Lower-scored memories (weakest removed first)
        3. Style hints (trimmed if budget is very tight)
        Never cut: system prompt, user message
        """
        budget = token_budget or self.default_budget

        # Fixed allocations (never cut)
        system_tokens = estimate_tokens(system_prompt)
        user_tokens = estimate_tokens(user_message)
        style_tokens = estimate_tokens(style_hint)

        fixed = system_tokens + user_tokens + self.response_headroom
        remaining = max(0, budget - fixed)

        # Dynamic allocations
        memory_budget = int(remaining * self.memory_ratio)
        history_budget = int(remaining * self.history_ratio)

        # If style hint doesn't fit, skip it
        if style_tokens > remaining * 0.05:
            style_hint = ""
        else:
            remaining -= style_tokens

        # Select memories (highest scored first, already sorted by reranker)
        selected_memories = self._select_within_budget(
            [m.get("text", "") for m in memories],
            memory_budget,
        )

        # Select history (newest first — keep recent context)
        history_texts = [
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in history
        ]
        selected_history = self._select_within_budget(
            list(reversed(history_texts)),
            history_budget,
        )
        selected_history.reverse()  # Restore chronological order

        # Assemble
        return self._assemble(
            system_prompt, selected_memories, selected_history,
            user_message, style_hint,
        )

    def _select_within_budget(
        self, items: List[str], budget: int
    ) -> List[str]:
        """Select items that fit within token budget."""
        selected = []
        used = 0
        for item in items:
            tokens = estimate_tokens(item)
            if used + tokens > budget:
                break
            selected.append(item)
            used += tokens
        return selected

    @staticmethod
    def _assemble(
        system_prompt: str,
        memories: List[str],
        history: List[str],
        user_message: str,
        style_hint: str,
    ) -> str:
        """Build the final prompt string."""
        parts = [system_prompt.strip()]

        if memories:
            memory_section = "\n".join(f"- {m}" for m in memories)
            parts.append(f"\nRelevant context about user:\n{memory_section}")

        if history:
            history_section = "\n".join(history)
            parts.append(f"\nChat History:\n{history_section}")

        parts.append(f"\nUser:\n{user_message}")

        if style_hint:
            parts.append(f"\n{style_hint}")

        parts.append(
            "\nInstructions:\n"
            "- Use memory only if relevant\n"
            "- Be precise\n"
            "- Do not echo the user message unless needed for clarity"
        )

        return "\n".join(parts)
