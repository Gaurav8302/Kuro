"""
Chat Manager v2 — Refactored for minimal, deterministic memory.

Replaces the old ChatManager that used:
  - RollingMemoryManager / progressive summarization
  - Fact extraction & importance scoring
  - Hash-based deduplication
  - Layered summaries injected during active sessions
  - Token trimming heuristics

New design:
  Layer 1  Active session: last N raw messages from MongoDB (no compression).
  Layer 2  Post-session:  ONE summary stored in Pinecone when session ≥ 50 msgs or closes.

No summarization during active conversation.
No fact extraction.  No importance scoring.  No hashing.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# New memory modules
# --------------------------------------------------------------------------
from memory.session_memory import session_memory
from memory.context_builder import build_context
from memory.long_term_memory import long_term_memory
from memory.model_lock import resolve_model

# --------------------------------------------------------------------------
# Existing utilities we keep
# --------------------------------------------------------------------------
from memory.chat_database import save_chat_to_db
from memory.user_profile import get_user_name as get_profile_name, set_user_name
from utils.kuro_prompt import build_kuro_prompt, sanitize_response
from utils.safety import validate_response, get_fallback_response
from utils.groq_client import GroqClient
from utils.token_estimator import estimate_tokens
from skills.skill_manager import skill_manager

# --------------------------------------------------------------------------
# Orchestrator (optional)
# --------------------------------------------------------------------------
try:
    from orchestration.llm_orchestrator import orchestrate as llm_orchestrate, client as unified_client
    ORCHESTRATOR_AVAILABLE = True
    logger.info("✅ LLM Orchestrator loaded successfully")
except ImportError as e:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning("⚠️ LLM Orchestrator not available: %s", e)

# Post-session summarization threshold (number of exchanges)
# Lowered from 50 to 6 so that short conversations get summarized too
POST_SESSION_SUMMARY_THRESHOLD = int(os.getenv("POST_SESSION_SUMMARY_THRESHOLD", "6"))


class ChatManager:
    """Memory-aware chat manager (v2 — minimal & deterministic)."""

    def __init__(self):
        try:
            self.groq_client = GroqClient()
            self._recent_responses: Dict[str, List[str]] = {}
            logger.info("✅ ChatManager v2 initialised (Groq client ready)")
        except Exception as e:
            logger.error("❌ Failed to initialise Groq client: %s", e)
            raise RuntimeError(f"AI model init failed: {e}")

    # ------------------------------------------------------------------
    # Name handling (unchanged)
    # ------------------------------------------------------------------
    _NAME_PATTERNS = [
        re.compile(r"my name is (\w+)", re.I),
        re.compile(r"i(?:'m| am) (\w+)", re.I),
        re.compile(r"call me (\w+)", re.I),
        re.compile(r"this is (\w+)", re.I),
        re.compile(r"i go by (\w+)", re.I),
    ]

    def extract_name(self, text: str) -> Optional[str]:
        for pat in self._NAME_PATTERNS:
            m = pat.search(text)
            if m:
                return m.group(1).capitalize()
        return None

    def get_user_name(self, user_id: str) -> Optional[str]:
        try:
            return get_profile_name(user_id)
        except Exception:
            return None

    def store_user_name(self, user_id: str, name: str, source_message: str):
        try:
            set_user_name(user_id, name)
            logger.info("Stored name '%s' for user %s", name, user_id)
        except Exception as e:
            logger.error("Failed to store user name: %s", e)

    # ------------------------------------------------------------------
    # Response repetition guard (kept, simplified)
    # ------------------------------------------------------------------
    def _check_response_repetition(self, user_id: str, response: str) -> bool:
        recent = self._recent_responses.get(user_id, [])
        new_words = set(response.lower().split())
        for prev in recent:
            prev_words = set(prev.lower().split())
            overlap = len(new_words & prev_words) / max(len(new_words), 1)
            if overlap > 0.8:
                return True
        return False

    def _store_response(self, user_id: str, response: str):
        if user_id not in self._recent_responses:
            self._recent_responses[user_id] = []
        self._recent_responses[user_id].append(response)
        self._recent_responses[user_id] = self._recent_responses[user_id][-3:]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def chat_with_memory(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
    ) -> str:
        """Process a user message within a session.

        Flow:
          1. Resolve user name.
          2. Build context (system + history + optional LT memory).
          3. Resolve model (session lock).
          4. Generate response via orchestrator or direct Groq call.
          5. Save exchange to MongoDB.
          6. Check if post-session summarization is needed.
          7. Return response.
        """
        request_start = time.time()
        session_id = session_id or "default"

        try:
            # --- 1. User name ---
            user_name = self.get_user_name(user_id) or "there"
            extracted_name = self.extract_name(message)
            if extracted_name and user_name == "there":
                self.store_user_name(user_id, extracted_name, message)
                user_name = extracted_name
                response = f"Nice to meet you, {user_name}! How can I help you?"
                save_chat_to_db(user_id, message, response, session_id)
                return response

            # --- 2. Build context (new deterministic builder) ---
            ctx = build_context(
                session_id=session_id,
                user_id=user_id,
                new_message=message,
                user_name=user_name,
            )
            debug = ctx["debug"]
            context_messages = ctx["messages"]
            system_prompt = ctx["system"]

            # --- 3. Model locking / resolution ---
            router_pick = "llama-3.3-70b-versatile"  # default conversation model
            try:
                from routing.model_router_v2 import get_best_model as get_best_model_v2
                import asyncio
                try:
                    asyncio.get_running_loop()
                    # Already in async context — just use default
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        v2 = loop.run_until_complete(get_best_model_v2(message, session_id=session_id))
                        router_pick = v2.get("chosen_model", router_pick)
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
            except Exception as e:
                logger.debug("Router v2 unavailable, using default model: %s", e)

            model_decision = resolve_model(
                session_id=session_id,
                user_message=message,
                router_pick=router_pick,
                context_tokens=debug["estimated_tokens"],
            )
            model_id = model_decision["model_id"]

            # --- Debug log (required for diagnosing memory issues) ---
            logger.info(
                "Memory retrieval triggered: %s", debug["long_term_triggered"],
            )
            logger.info(
                "Memories injected: %s",
                debug.get("long_term_texts", []) if debug["long_term_count"] > 0 else "[]",
            )
            logger.info("Recent messages count: %d", debug["messages_injected"])
            logger.info("Model used: %s (source=%s)", model_id, model_decision["source"])
            logger.info(
                "Memory debug | session=%s tokens=%d LT_reason=%s LT_count=%d",
                session_id,
                debug["estimated_tokens"],
                debug["long_term_reason"],
                debug["long_term_count"],
            )

            # --- 4. Generate response ---
            response_text = self._generate_response(
                message=message,
                system_prompt=system_prompt,
                context_messages=context_messages,
                model_id=model_id,
                user_name=user_name,
                session_id=session_id,
            )

            # Repetition check
            if self._check_response_repetition(user_id, response_text):
                logger.info("Repetitive response detected, regenerating with variation hint")
                variation_system = system_prompt + (
                    "\n\nIMPORTANT: Vary your response. Do not repeat previous phrasing."
                )
                response_text = self._generate_response(
                    message=message,
                    system_prompt=variation_system,
                    context_messages=context_messages,
                    model_id=model_id,
                    user_name=user_name,
                    session_id=session_id,
                )
            self._store_response(user_id, response_text)

            # --- 5. Persist exchange ---
            save_chat_to_db(user_id, message, response_text, session_id)

            # --- 6. Post-session summarization check ---
            # Trigger summarization when message count first crosses the threshold,
            # and then every POST_SESSION_SUMMARY_THRESHOLD messages after that.
            msg_count = session_memory.get_message_count(session_id)
            if msg_count >= POST_SESSION_SUMMARY_THRESHOLD and msg_count % POST_SESSION_SUMMARY_THRESHOLD == 0:
                logger.info(
                    "Post-session summary trigger: session=%s msg_count=%d threshold=%d",
                    session_id, msg_count, POST_SESSION_SUMMARY_THRESHOLD,
                )
                self._trigger_post_session_summary(user_id, session_id)

            elapsed_ms = int((time.time() - request_start) * 1000)
            logger.info(
                "Chat response generated for %s in %dms (model=%s)",
                user_name, elapsed_ms, model_id,
            )
            return response_text

        except Exception as e:
            logger.error("Error in chat processing: %s", e, exc_info=True)
            return "I apologise, but I encountered an error processing your message. Please try again."

    # ------------------------------------------------------------------
    # Response generation (supports orchestrator or direct Groq)
    # ------------------------------------------------------------------
    def _generate_response(
        self,
        message: str,
        system_prompt: str,
        context_messages: List[Dict[str, str]],
        model_id: str,
        user_name: str,
        session_id: str,
    ) -> str:
        """Generate a response using the orchestrator or falling back to direct Groq."""

        # Try the full orchestrator path first (includes routing, circuit breaker, etc.)
        if ORCHESTRATOR_AVAILABLE:
            try:
                import asyncio
                try:
                    asyncio.get_running_loop()
                    # In async context — skip orchestrator to avoid nested loop
                    logger.debug("Async context detected, using direct generation")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            llm_orchestrate(
                                user_message=message,
                                system_prompt=system_prompt,
                                memory_context=None,  # context is already in system_prompt / messages
                                developer_forced_model=model_id,
                                session_id=session_id,
                            )
                        )
                        reply = result.get("reply", "")
                        if reply:
                            sanitized = sanitize_response(reply)
                            is_valid, _ = validate_response(sanitized, None)
                            if is_valid:
                                return sanitized
                            logger.warning("Orchestrator reply failed safety check, falling back to direct Groq")
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
            except Exception as e:
                logger.warning("Orchestrator failed, using direct Groq: %s", e)

        # Direct fallback: GroqClient with the assembled messages
        try:
            # Build a single prompt string from context messages for the direct client
            history_text = ""
            for m in context_messages:
                if m["role"] == "system":
                    continue  # system prompt handled separately
                if m["role"] == "user":
                    history_text += f"User: {m['content']}\n"
                elif m["role"] == "assistant":
                    history_text += f"Assistant: {m['content']}\n"

            prompt = history_text + f"User: {message}" if history_text else message

            response = self.groq_client.generate_content(
                prompt=prompt,
                system_instruction=system_prompt,
            )
            if response:
                return sanitize_response(response)
        except Exception as e:
            logger.error("Direct Groq generation failed: %s", e)

        return get_fallback_response(message)

    # ------------------------------------------------------------------
    # Post-session summarization (non-blocking)
    # ------------------------------------------------------------------
    def _trigger_post_session_summary(self, user_id: str, session_id: str):
        """Fire-and-forget session summarisation in a background thread."""
        import threading

        def _summarize():
            try:
                messages = session_memory.get_recent_messages(session_id, limit=200)
                if len(messages) < 10:
                    return
                long_term_memory.summarize_session(
                    user_id=user_id,
                    session_id=session_id,
                    messages=messages,
                )
                logger.info("Post-session summary generated for session %s", session_id)
            except Exception as e:
                logger.error("Post-session summarization failed: %s", e)

        thread = threading.Thread(target=_summarize, daemon=True)
        thread.start()


# --------------------------------------------------------------------------
# Global instance & backward-compatible exports
# --------------------------------------------------------------------------
chat_manager = ChatManager()


def chat_with_memory(
    user_id: str,
    message: str,
    session_id: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """Backward-compatible function wrapper."""
    return chat_manager.chat_with_memory(user_id, message, session_id, top_k)
