"""Long-Term Memory — Layer 2 (Post-Session).

Handles:
  1. Post-session summarization (ONE summary per session, stored in Pinecone).
  2. Semantic retrieval of past session summaries with trigger detection.

Trigger conditions for retrieval:
  - User message contains recall phrases ("last time", "previous session", …)
  - Semantic similarity > 0.85 threshold

No progressive summarization. No layered summaries. No fact extraction.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trigger phrases that activate long-term memory retrieval
# ---------------------------------------------------------------------------
RECALL_PHRASES: List[re.Pattern] = [
    re.compile(r"\blast\s+time\b", re.IGNORECASE),
    re.compile(r"\bprevious\s+session\b", re.IGNORECASE),
    re.compile(r"\bremember\s+when\b", re.IGNORECASE),
    re.compile(r"\bwe\s+talked\s+about\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+remember\b", re.IGNORECASE),
    re.compile(r"\brecall\s+(our|the)\b", re.IGNORECASE),
    re.compile(r"\bearlier\s+conversation\b", re.IGNORECASE),
    re.compile(r"\bpast\s+conversation\b", re.IGNORECASE),
    re.compile(r"\bbefore\s+we\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+did\s+we\s+(talk|discuss)\b", re.IGNORECASE),
]

SIMILARITY_THRESHOLD = 0.85
TOP_K_RESULTS = 3


def should_retrieve_long_term(message: str) -> Tuple[bool, str]:
    """Determine whether to query Pinecone for past session summaries.

    Returns:
        (should_retrieve: bool, reason: str)
    """
    if not message:
        return False, "empty_message"

    for pattern in RECALL_PHRASES:
        if pattern.search(message):
            return True, f"phrase_match:{pattern.pattern}"

    return False, "no_trigger"


class LongTermMemory:
    """Post-session summarization + retrieval via Pinecone.

    Public API:
        summarize_session(user_id, session_id, messages, summarizer) -> str | None
        retrieve(query, user_id, top_k) -> List[dict]
        should_retrieve(message) -> (bool, str)
    """

    def __init__(self):
        self._index = None  # lazy-loaded Pinecone index
        self._embedding_fn = None  # lazy-loaded embedding function

    # ------------------------------------------------------------------
    # Lazy Pinecone + Gemini initialisation
    # ------------------------------------------------------------------
    def _ensure_clients(self):
        """Initialise Pinecone index and Gemini embeddings on first use."""
        if self._index is not None:
            return

        import os

        # --- Gemini embeddings ---
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY required for long-term memory embeddings")
        genai.configure(api_key=api_key)
        embedding_model = "models/text-embedding-004"

        def _embed(text: str) -> List[float]:
            result = genai.embed_content(
                model=embedding_model,
                content=text,
                task_type="retrieval_document",
            )
            vec = result["embedding"]
            # Pinecone index expects 384 dims; Gemini returns 768 — downsample
            if len(vec) > 384:
                vec = vec[::2][:384]
            elif len(vec) < 384:
                vec.extend([0.0] * (384 - len(vec)))
            return vec

        self._embedding_fn = _embed

        # --- Pinecone ---
        from pinecone import Pinecone

        pc_api_key = os.getenv("PINECONE_API_KEY")
        if not pc_api_key:
            raise RuntimeError("PINECONE_API_KEY required for long-term memory")

        pc = Pinecone(api_key=pc_api_key)
        index_name = os.getenv("PINECONE_INDEX_NAME", "my-chatbot-memory")
        self._index = pc.Index(index_name)
        logger.info("LongTermMemory: Pinecone index '%s' connected", index_name)

    # ------------------------------------------------------------------
    # Post-session summarization (Layer 2)
    # ------------------------------------------------------------------
    def summarize_session(
        self,
        user_id: str,
        session_id: str,
        messages: List[Dict[str, str]],
        summarizer_fn=None,
    ) -> Optional[str]:
        """Generate ONE summary for the full session and store in Pinecone.

        Args:
            user_id: owner
            session_id: session identifier
            messages: list of {"role": ..., "content": ...}
            summarizer_fn: callable(prompt: str) -> str  (LLM call)

        Returns:
            The summary text, or None on failure.
        """
        if not messages or len(messages) < 4:
            logger.debug("LongTermMemory: session %s too short to summarize", session_id)
            return None

        # Build a plain-text transcript for the summarizer
        transcript_lines = []
        for m in messages:
            role = m.get("role", "user").capitalize()
            transcript_lines.append(f"{role}: {m.get('content', '')}")
        transcript = "\n".join(transcript_lines)

        prompt = (
            "Summarize the following conversation in 3-5 concise sentences. "
            "Capture the main topics, decisions, and any action items. "
            "Do NOT extract individual facts. Just provide a cohesive narrative summary.\n\n"
            f"--- Conversation ---\n{transcript}\n--- End ---\n\nSummary:"
        )

        summary: Optional[str] = None
        if summarizer_fn:
            try:
                summary = summarizer_fn(prompt)
            except Exception as e:
                logger.error("LongTermMemory: summarization failed: %s", e)
                return None
        else:
            # Fallback: use Groq client
            try:
                from utils.groq_client import GroqClient

                client = GroqClient()
                summary = client.generate_content(prompt)
            except Exception as e:
                logger.error("LongTermMemory: Groq summarisation failed: %s", e)
                return None

        if not summary:
            return None

        # Store in Pinecone
        try:
            self._ensure_clients()
            vec = self._embedding_fn(summary)
            meta = {
                "text": summary[:2000],  # Pinecone metadata limit
                "user_id": user_id,
                "session_id": session_id,
                "summary_type": "session_summary",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user": user_id,  # compat with existing filter patterns
            }
            vec_id = f"sess_summary_{session_id}_{uuid.uuid4().hex[:8]}"
            self._index.upsert([(vec_id, vec, meta)])
            logger.info(
                "LongTermMemory: stored summary for session %s (%d chars)",
                session_id,
                len(summary),
            )
        except Exception as e:
            logger.error("LongTermMemory: Pinecone upsert failed: %s", e)
            # Summary was generated; just not stored in vector DB
            # Still return it so caller can log/store elsewhere

        return summary

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = TOP_K_RESULTS,
    ) -> List[Dict[str, Any]]:
        """Retrieve top-k past session summaries from Pinecone.

        Returns list of {"text": ..., "score": ..., "session_id": ..., "timestamp": ...}
        """
        try:
            self._ensure_clients()
            query_vec = self._embedding_fn(query)
            results = self._index.query(
                vector=query_vec,
                top_k=top_k,
                include_metadata=True,
                filter={"user": user_id, "summary_type": "session_summary"},
            )
            out = []
            for match in results.matches:
                score = float(match.score)
                # Only include results above similarity threshold
                if score >= SIMILARITY_THRESHOLD:
                    out.append({
                        "text": match.metadata.get("text", ""),
                        "score": score,
                        "session_id": match.metadata.get("session_id", ""),
                        "timestamp": match.metadata.get("timestamp", ""),
                    })
            logger.debug(
                "LongTermMemory: retrieved %d summaries (of %d candidates) for user %s",
                len(out),
                len(results.matches),
                user_id,
            )
            return out
        except Exception as e:
            logger.error("LongTermMemory: retrieval failed: %s", e)
            return []

    def should_retrieve(self, message: str) -> Tuple[bool, str]:
        """Convenience wrapper around module-level trigger check."""
        return should_retrieve_long_term(message)


# Global singleton
long_term_memory = LongTermMemory()

__all__ = [
    "LongTermMemory",
    "long_term_memory",
    "should_retrieve_long_term",
    "SIMILARITY_THRESHOLD",
]
