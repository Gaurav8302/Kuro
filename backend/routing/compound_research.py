"""Groq Compound Research — wraps groq/compound-mini for web search.

The compound-mini model performs real-time web search and returns
synthesized results. This module:
  1. Calls groq/compound-mini with the user query.
  2. Truncates the result to 4000 characters.
  3. Never sends compound output directly to the user — it must be
     passed to the reasoning model along with conversation memory.
"""
from __future__ import annotations

import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_COMPOUND_MODEL = "groq/compound-mini"
_MAX_RESEARCH_CHARS = 4000


def run_compound_research(query: str) -> Optional[str]:
    """Execute a compound-mini research call and return truncated context.

    Returns:
        Research context string (max 4000 chars), or None on failure.
    """
    logger.info("Compound research START: model=%s query=%.100s", _COMPOUND_MODEL, query)

    if not _GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set — cannot run compound research")
        return None

    try:
        payload = {
            "model": _COMPOUND_MODEL,
            "messages": [{"role": "user", "content": query}],
            "temperature": 0.2,
            "max_tokens": 2048,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {_GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        import time as _time
        _start = _time.time()

        response = requests.post(
            f"{_GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )

        _elapsed = int((_time.time() - _start) * 1000)
        logger.info("Compound research HTTP %d in %dms", response.status_code, _elapsed)

        if response.status_code != 200:
            logger.warning(
                "Compound research returned status %d: %s",
                response.status_code,
                response.text[:300],
            )
            return None

        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not content:
            logger.warning("Compound research returned empty content")
            return None

        # Truncate to max chars
        if len(content) > _MAX_RESEARCH_CHARS:
            content = content[:_MAX_RESEARCH_CHARS]

        logger.info("Compound research completed: %d chars", len(content))
        return content

    except requests.exceptions.Timeout:
        logger.warning("Compound research timed out")
        return None
    except Exception as e:
        logger.error("Compound research failed: %s", e)
        return None
