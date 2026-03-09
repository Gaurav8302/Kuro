"""Context Builder — builds the final LLM prompt context.

Implements the specification:
  1. Fetch last N messages for session (raw, role-tagged).
  2. Optionally prepend retrieved long-term memories (if triggered).
  3. Prepend system prompt.
  4. Append user message.

Returns a structured dict ready for LLM consumption:
  {
    "system": str,
    "messages": [{"role": ..., "content": ...}, ...],
    "debug": {
        "messages_injected": int,
        "estimated_tokens": int,
        "long_term_triggered": bool,
        "long_term_reason": str,
        "long_term_count": int,
        "long_term_texts": list,
    }
  }
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional, List

from memory.session_memory import session_memory
from memory.long_term_memory import long_term_memory
from utils.token_estimator import estimate_tokens

logger = logging.getLogger(__name__)

# Maximum context tokens before we start trimming oldest messages.
# Default 28 000 leaves headroom for a 32k-token model.
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "28000"))

# Number of exchanges to fetch from the active session.
EXCHANGE_LIMIT = int(os.getenv("SESSION_EXCHANGE_LIMIT", "15"))


def _load_system_prompt(task_type: str = "conversation") -> str:
    """Load the base Kuro system prompt for the given task type."""
    try:
        from utils.kuro_prompt import build_system_instruction
        return build_system_instruction(task_type)
    except Exception:
        return (
            "You are Kuro, an AI assistant created by Gaurav. "
            "You have access to a contextual memory system. "
            "If relevant past context is provided, reference it naturally. "
            "Never claim you cannot remember previous conversations if context is present."
        )


def build_context(
    session_id: str,
    user_id: str,
    new_message: str,
    user_name: Optional[str] = None,
    system_prompt_override: Optional[str] = None,
    max_tokens: Optional[int] = None,
    task_type: str = "conversation",
) -> Dict[str, Any]:
    """Build the complete context payload for an LLM call.

    Steps:
      1. Fetch last N messages for session from MongoDB.
      2. Filter by session_id; sort ascending by timestamp.
      3. Limit to EXCHANGE_LIMIT exchanges.
      4. Check long-term memory trigger.
      5. If triggered, retrieve top 3 from Pinecone and prepend.
      6. Assemble: system prompt → optional past context → conversation history → user message.
      7. Trim oldest non-system messages only if exceeding model context limit.

    Returns:
        dict with keys: system, messages, debug
    """
    max_ctx = max_tokens or MAX_CONTEXT_TOKENS

    # --- 1. System prompt (task-aware) ---
    system_prompt = system_prompt_override or _load_system_prompt(task_type)
    if user_name and user_name != "there":
        system_prompt += f"\n\nThe user's name is {user_name}."

    # --- 2. Active session history (Layer 1) ---
    history_messages = session_memory.get_recent_messages(
        session_id, limit=EXCHANGE_LIMIT
    )

    # --- 3. Long-term memory check (Layer 2) ---
    lt_triggered, lt_reason = long_term_memory.should_retrieve(new_message)
    lt_results: List[Dict[str, Any]] = []
    lt_context_text = ""

    # Debug: log trigger decision
    logger.info(
        "Memory retrieval triggered: %s (reason: %s) for message: %.100s",
        lt_triggered, lt_reason, new_message,
    )

    if lt_triggered:
        try:
            lt_results = long_term_memory.retrieve(new_message, user_id)
            if lt_results:
                lines = ["\nRelevant Past Context (from previous conversations):"]
                for i, r in enumerate(lt_results, 1):
                    lines.append(f"  {i}. {r['text']}")
                lt_context_text = "\n".join(lines)
                logger.info("Memories injected: %d", len(lt_results))
                for i, r in enumerate(lt_results, 1):
                    logger.info(
                        "  Memory %d (score=%.4f): %.120s",
                        i, r.get("score", 0), r["text"][:120],
                    )
            else:
                logger.info("Memories injected: 0 (retrieval returned empty)")
        except Exception as e:
            logger.warning("Context builder: long-term retrieval failed: %s", e)
    else:
        logger.info("Memories injected: 0 (retrieval not triggered)")

    # --- 4. Assemble messages list ---
    messages: List[Dict[str, str]] = []

    # System message — memories go into the system prompt for maximum visibility
    full_system = system_prompt
    if lt_context_text:
        full_system += "\n\n" + lt_context_text
    messages.append({"role": "system", "content": full_system})

    # Conversation history (raw, role-tagged)
    messages.extend(history_messages)

    # New user message
    messages.append({"role": "user", "content": new_message})

    # --- 5. Token budget check & trim ---
    total_tokens = sum(estimate_tokens(m["content"]) for m in messages)

    if total_tokens > max_ctx:
        logger.warning(
            "Context builder: %d tokens exceeds limit %d — trimming oldest turns",
            total_tokens,
            max_ctx,
        )
        # Keep system (index 0) and new user message (last).
        # Trim oldest conversation messages from the middle.
        system_msg = messages[0]
        user_msg = messages[-1]
        middle = messages[1:-1]

        # Remove from the front (oldest) until under budget
        reserved = estimate_tokens(system_msg["content"]) + estimate_tokens(user_msg["content"])
        remaining_budget = max_ctx - reserved
        kept = []
        running = 0
        # Iterate in reverse (newest first) to keep recent turns
        for m in reversed(middle):
            t = estimate_tokens(m["content"])
            if running + t <= remaining_budget:
                kept.append(m)
                running += t
            else:
                break
        kept.reverse()
        messages = [system_msg] + kept + [user_msg]
        total_tokens = sum(estimate_tokens(m["content"]) for m in messages)

    # --- 6. Debug metadata ---
    exchange_count = sum(1 for m in messages if m["role"] == "user")
    debug_info = {
        "messages_injected": len(messages) - 2,  # exclude system + new user msg
        "exchange_count": exchange_count,
        "estimated_tokens": total_tokens,
        "long_term_triggered": lt_triggered,
        "long_term_reason": lt_reason,
        "long_term_count": len(lt_results),
        "long_term_texts": [r.get("text", "")[:200] for r in lt_results],
    }

    logger.info(
        "Context built: %d history msgs, ~%d tokens, LT=%s (%s, %d results)",
        debug_info["messages_injected"],
        total_tokens,
        lt_triggered,
        lt_reason,
        len(lt_results),
    )
    logger.info("Recent messages count: %d", len(history_messages))

    return {
        "system": full_system,
        "messages": messages,
        "debug": debug_info,
    }


__all__ = ["build_context"]
