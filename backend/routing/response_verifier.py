"""2-Stage Response Verifier — checks LLM draft answers for hallucination risk.

Architecture:
  Stage 1: LLM generates a draft answer (happens in normal pipeline)
  Stage 2: This module checks whether the draft contains risky content

The verifier uses the SAME model (no extra cost for a second model) with a
focused verification prompt. Cost increase: ~15-20% per verified response.

Only triggered when the time-sensitive classifier flags a query as borderline
(i.e., the classifier wasn't sure enough to outright block, but there's risk).

Returns: SAFE, REQUIRES_BROWSER, or NEEDS_CLARIFICATION
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Verification categories
# ---------------------------------------------------------------------------
SAFE = "SAFE"
REQUIRES_BROWSER = "REQUIRES_BROWSER"
NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"

# ---------------------------------------------------------------------------
# Verification prompt template
# ---------------------------------------------------------------------------
_VERIFICATION_PROMPT = """You are a fact safety verifier for an AI assistant called Kuro.

Your job is to check if the answer below contains information that might be outdated, incorrect, or hallucinated.

Check if the answer contains:
1. Specific names of current political leaders (presidents, prime ministers, chief ministers, governors, etc.)
2. Current news events or recent happenings
3. Stock prices, market data, or financial figures
4. Sports scores or match results
5. Election results or political developments
6. Any claim about what is "currently" true that could have changed
7. A fabricated knowledge cutoff date (e.g., "as of my knowledge in September 2025")
8. Weather or real-time data

If the answer contains ANY of the above, respond with exactly: REQUIRES_BROWSER
If the answer asks the user for clarification, respond with exactly: SAFE
If the answer is about general knowledge, concepts, or static facts that don't change, respond with exactly: SAFE

Respond with ONLY one word: SAFE or REQUIRES_BROWSER

---

Question: {question}
Answer: {answer}"""


def _is_browser_search_recommendation_only(draft_answer: str) -> bool:
    """Return True only for answers that are purely a browser-search recommendation.

    This prevents a factual answer from bypassing verification just because it
    appends a generic recency disclaimer.
    """
    normalized = re.sub(r"\s+", " ", draft_answer).strip()
    if not normalized:
        return False

    recommendation_patterns = [
        r"^my knowledge may be outdated on this topic\.? you can enable (?:\*\*?)?browser search",
        r"^this question involves time-sensitive information.*you can enable (?:\*\*?)?browser search",
        r"^i(?:'d| would)? recommend enabling (?:\*\*?)?browser search",
        r"^to make sure you get the right answer, i(?:'d| would)? recommend enabling (?:\*\*?)?browser search",
    ]

    lowered = normalized.lower()
    return any(re.search(pattern, lowered) for pattern in recommendation_patterns)


def verify_response(
    question: str,
    draft_answer: str,
    model_id: str = "llama-3.1-8b-instant",
) -> str:
    """Verify a draft LLM response for hallucination risk.

    Uses the same Groq API with a lightweight verification prompt.
    Falls back to SAFE if verification fails (to avoid blocking responses).

    Args:
        question: The original user question
        draft_answer: The LLM's draft response to verify
        model_id: Model to use for verification (defaults to fast model)

    Returns:
        One of: SAFE, REQUIRES_BROWSER, NEEDS_CLARIFICATION
    """
    # Skip verification for very short or obviously safe responses
    if len(draft_answer) < 20:
        return SAFE

    # Only bypass verification when the draft is purely a search recommendation.
    if _is_browser_search_recommendation_only(draft_answer):
        return SAFE

    # Quick regex pre-check: if draft asks for clarification, it's safe
    if re.search(r"which country|could you (specify|clarify)|more (context|details|specific)", draft_answer, re.I):
        return SAFE

    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        logger.warning("GROQ_API_KEY not set — skipping verification")
        return SAFE

    try:
        import requests

        prompt = _VERIFICATION_PROMPT.format(
            question=question[:500],
            answer=draft_answer[:1000],
        )

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 10,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=5,
        )

        if resp.status_code != 200:
            logger.warning("Verification call returned %d", resp.status_code)
            return SAFE

        content = (
            resp.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
            .upper()
        )

        if "REQUIRES_BROWSER" in content:
            logger.info("Verifier flagged response as REQUIRES_BROWSER")
            return REQUIRES_BROWSER
        if "NEEDS_CLARIFICATION" in content:
            logger.info("Verifier flagged response as NEEDS_CLARIFICATION")
            return NEEDS_CLARIFICATION

        return SAFE

    except Exception as e:
        logger.warning("Verification failed (defaulting to SAFE): %s", e)
        return SAFE


# ---------------------------------------------------------------------------
# Safe response for verified-unsafe answers
# ---------------------------------------------------------------------------

_BROWSER_SUGGESTION = (
    "I tried to answer this, but my response may include outdated or unverifiable information. "
    "To make sure you get the right answer, I'd recommend enabling **browser search** (🌐) — "
    "that way I can pull in real-time, verified data for you."
)


def get_verification_safe_response() -> str:
    """Return the standard safe response when verification flags an answer."""
    return _BROWSER_SUGGESTION


__all__ = [
    "verify_response",
    "get_verification_safe_response",
    "SAFE",
    "REQUIRES_BROWSER",
    "NEEDS_CLARIFICATION",
]
