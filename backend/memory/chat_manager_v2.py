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

v3 router integration:
  - LLM-based router classifier (model_router_v3)
  - Compound research pipeline (groq/compound-mini)
  - search_mode support for manual web search trigger

No summarization during active conversation.
No fact extraction.  No importance scoring.  No hashing.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional, List, Dict, Any, Tuple

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
from config.model_config import SKILL_TO_MODEL, normalize_model_id
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
    logger.info("LLM Orchestrator loaded successfully")
except ImportError as e:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning("LLM Orchestrator not available: %s", e)

# --------------------------------------------------------------------------
# Router v3 + compound research
# --------------------------------------------------------------------------
try:
    from routing.model_router_v3 import (
        get_best_model as get_best_model_v3,
        needs_research,
        REASONING_MODEL,
    )
    from routing.compound_research import run_compound_research
    ROUTER_V3_AVAILABLE = True
    logger.info("Router v3 + compound research loaded successfully")
except Exception as e:
    ROUTER_V3_AVAILABLE = False
    logger.warning("Router v3 not available, falling back to v2: %s (type: %s)", e, type(e).__name__)

# --------------------------------------------------------------------------
# Time-sensitive classifier + 2-stage verifier
# --------------------------------------------------------------------------
try:
    from routing.time_sensitive_classifier import classify_time_sensitivity, get_safe_response
    from routing.response_verifier import verify_response, get_verification_safe_response, REQUIRES_BROWSER
    SAFETY_CLASSIFIER_AVAILABLE = True
    logger.info("Time-sensitive classifier + response verifier loaded successfully")
except Exception as e:
    SAFETY_CLASSIFIER_AVAILABLE = False
    logger.warning("Safety classifier not available: %s", e)

# Post-session summarization threshold (number of exchanges)
# Lowered from 50 to 6 so that short conversations get summarized too
POST_SESSION_SUMMARY_THRESHOLD = int(os.getenv("POST_SESSION_SUMMARY_THRESHOLD", "6"))

UI_SKILL_TO_TASK_TYPE: Dict[str, str] = {
    "code": "code",
    "creative": "conversation",
    "problem": "reasoning",
    "explain": "summarization",
    "web": "research",
}

UI_SKILL_TO_ROUTER_SKILL: Dict[str, str] = {
    "code": "code",
    "creative": "conversation",
    "problem": "reasoning",
    "explain": "summarization",
    "web": "research",
}

_LIVE_RESEARCH_SYSTEM_OVERRIDE = """LIVE RESEARCH MODE:
- Browser search/web research is already enabled for this turn.
- The provided research context contains the live information you should use if it is relevant.
- Answer directly from the research context when it supports the answer.
- Do not tell the user to enable browser search, web search, or search again when research context is already provided.
- Do not add generic warnings like 'my knowledge may be outdated' if the answer is supported by the research context.
- Only mention uncertainty when the research context is conflicting, incomplete, or does not answer the question."""

_REDUNDANT_SEARCH_WARNING_PATTERNS = [
    re.compile(r"(?:^|\n)\s*My knowledge may be outdated on this topic\..*(?=\n|$)", re.I),
    re.compile(r"(?:^|\n)\s*This question involves time-sensitive information.*?(?=\n|$)", re.I),
    re.compile(r"(?:^|\n)\s*Political roles change over time, so my information may be outdated\..*(?=\n|$)", re.I),
    re.compile(r"(?:^|\n)\s*You can enable\s+\*\*?browser search\*\*?.*(?=\n|$)", re.I),
    re.compile(r"(?:^|\n)\s*I'd also recommend enabling\s+\*\*?browser search\*\*?.*(?=\n|$)", re.I),
    re.compile(r"(?:^|\n)\s*I'd recommend enabling\s+\*\*?browser search\*\*?.*(?=\n|$)", re.I),
    re.compile(r"(?:^|\n)\s*To make sure you get the right answer, I'd recommend enabling\s+\*\*?browser search\*\*?.*(?=\n|$)", re.I),
]


def _strip_redundant_search_warning(response_text: str) -> str:
    """Remove stale search-enable advisories from responses already backed by live research."""
    cleaned = response_text
    for pattern in _REDUNDANT_SEARCH_WARNING_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or response_text.strip()


class ChatManager:
    """Memory-aware chat manager (v2 — minimal & deterministic)."""

    def __init__(self):
        try:
            self.groq_client = GroqClient()
            self._recent_responses: Dict[str, List[str]] = {}
            logger.info("ChatManager v2 initialised (Groq client ready)")
        except Exception as e:
            logger.error("Failed to initialise Groq client: %s", e)
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
        search_mode: bool = False,
        skill: str = "auto",
    ) -> Tuple[str, str, str]:
        """Process a user message within a session.

        Flow:
          1. Resolve user name.
          2. Build context (system + history + optional LT memory).
          3. Route via v3 router (LLM classifier).
          4. Run compound research if needed or search_mode is True.
          5. Generate response via orchestrator or direct Groq call.
          6. Save exchange to MongoDB.
          7. Check if post-session summarization is needed.

        Returns:
            Tuple of (response_text, model_used, route_rule)
        """
        request_start = time.time()
        session_id = session_id or "default"
        model_id = "llama-3.1-8b-instant"
        route_rule = "default"

        logger.info(
            "chat_with_memory called: user=%s session=%s search_mode=%s skill=%s router_v3=%s",
            user_id[:20], session_id[:30], search_mode, skill, ROUTER_V3_AVAILABLE,
        )

        try:
            # --- 1. User name ---
            user_name = self.get_user_name(user_id) or "there"
            extracted_name = self.extract_name(message)
            if extracted_name and user_name == "there":
                self.store_user_name(user_id, extracted_name, message)
                user_name = extracted_name
                response = f"Nice to meet you, {user_name}! How can I help you?"
                save_chat_to_db(user_id, message, response, session_id)
                return response, "greeting", "name_extraction"

            # --- 2. Pre-check: Time-sensitive classification ---
            time_sensitivity = None
            if SAFETY_CLASSIFIER_AVAILABLE and not search_mode:
                time_sensitivity = classify_time_sensitivity(message)
                if time_sensitivity["is_time_sensitive"]:
                    logger.info(
                        "Time-sensitive query detected: category=%s reason=%s confidence=%.2f",
                        time_sensitivity["category"],
                        time_sensitivity["reason"],
                        time_sensitivity["confidence"],
                    )
                    # High-confidence time-sensitive: return safe response immediately
                    if time_sensitivity["confidence"] >= 0.85:
                        safe_response = get_safe_response(time_sensitivity, message)
                        save_chat_to_db(user_id, message, safe_response, session_id)
                        elapsed_ms = int((time.time() - request_start) * 1000)
                        logger.info(
                            "Returned safe response for time-sensitive query in %dms",
                            elapsed_ms,
                        )
                        return safe_response, "safety_classifier", "time_sensitive_blocked"

            # --- 3. Build context (new deterministic builder) ---
            ctx = build_context(
                session_id=session_id,
                user_id=user_id,
                new_message=message,
                user_name=user_name,
            )
            debug = ctx["debug"]
            context_messages = ctx["messages"]
            system_prompt = ctx["system"]

            # --- 4. Router selection (manual override or automatic routing) ---
            research_required = False
            research_context: Optional[str] = None
            task_type = "conversation"  # default

            normalized_skill = (skill or "auto").strip().lower()
            manual_skill_selected = normalized_skill in UI_SKILL_TO_ROUTER_SKILL

            if manual_skill_selected:
                mapped_skill = UI_SKILL_TO_ROUTER_SKILL[normalized_skill]
                router_pick = normalize_model_id(SKILL_TO_MODEL[mapped_skill])
                task_type = UI_SKILL_TO_TASK_TYPE.get(normalized_skill, "conversation")
                research_required = normalized_skill == "web"
                route_rule = f"manual_skill:{normalized_skill}"
                if research_required:
                    search_mode = True
                logger.info(
                    "Manual skill override active: ui_skill=%s mapped_skill=%s model=%s",
                    normalized_skill,
                    mapped_skill,
                    router_pick,
                )
            elif ROUTER_V3_AVAILABLE:
                try:
                    v3_decision = get_best_model_v3(
                        query=message,
                        session_id=session_id,
                        search_mode=search_mode,
                    )
                    router_pick = v3_decision.get("chosen_model", "llama-3.1-8b-instant")
                    research_required = v3_decision.get("research_required", False)
                    task_type = v3_decision.get("task_type", "conversation")
                    confidence_escalated = v3_decision.get("confidence_escalated", False)
                    route_rule = f"v3:{task_type}:{v3_decision.get('complexity', 'simple')}"
                    if confidence_escalated:
                        route_rule += ":escalated"
                    logger.info(
                        "Router v3: model=%s task=%s complexity=%s research=%s conf=%.2f escalated=%s",
                        router_pick,
                        v3_decision.get("task_type"),
                        v3_decision.get("complexity"),
                        research_required,
                        v3_decision.get("confidence", 0),
                        confidence_escalated,
                    )
                except Exception as e:
                    logger.warning("Router v3 failed, falling back to v2: %s", e)
                    router_pick = self._fallback_to_v2(message, session_id)
                    route_rule = "v2_fallback"
            else:
                router_pick = self._fallback_to_v2(message, session_id)
                route_rule = "v2_fallback"

            # --- 4b. Rebuild system prompt with task-specific instructions ---
            if task_type != "conversation":
                ctx = build_context(
                    session_id=session_id,
                    user_id=user_id,
                    new_message=message,
                    user_name=user_name,
                    task_type=task_type,
                )
                context_messages = ctx["messages"]
                system_prompt = ctx["system"]

            # --- 5. Compound research (if needed or manual search_mode) ---
            if (research_required or search_mode) and ROUTER_V3_AVAILABLE:
                try:
                    logger.info("Running compound research for query: %.100s", message)
                    research_context = run_compound_research(message)
                    if research_context:
                        logger.info("Compound research returned %d chars", len(research_context))
                        # Force reasoning model when research is used
                        router_pick = REASONING_MODEL
                        route_rule += ":research"
                    else:
                        logger.warning("Compound research returned empty result")
                except Exception as e:
                    logger.error("Compound research failed: %s", e)

            # --- 6. Model locking / resolution ---
            if manual_skill_selected:
                model_id = router_pick
                model_decision = {"model_id": model_id, "source": "manual_skill_override"}
            else:
                model_decision = resolve_model(
                    session_id=session_id,
                    user_message=message,
                    router_pick=router_pick,
                    context_tokens=debug["estimated_tokens"],
                )
                model_id = model_decision["model_id"]

            # --- Debug log ---
            logger.info("Memory retrieval triggered: %s", debug["long_term_triggered"])
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

            # --- 7. Generate response ---
            if research_context:
                # When research is available, build a structured prompt
                response_text = self._generate_research_response(
                    message=message,
                    system_prompt=system_prompt,
                    context_messages=context_messages,
                    model_id=model_id,
                    research_context=research_context,
                    session_id=session_id,
                )
            else:
                response_text = self._generate_response(
                    message=message,
                    system_prompt=system_prompt,
                    context_messages=context_messages,
                    model_id=model_id,
                    user_name=user_name,
                    session_id=session_id,
                )

            # --- Stage 2 verification (BORDERLINE only: 0.40 ≤ conf < 0.85) ---
            if (
                SAFETY_CLASSIFIER_AVAILABLE
                and not search_mode
                and not research_context
                and time_sensitivity
                and time_sensitivity.get("is_time_sensitive")
                and 0.40 <= time_sensitivity["confidence"] < 0.85
            ):
                verification = verify_response(message, response_text, model_id="llama-3.1-8b-instant")
                if verification == REQUIRES_BROWSER:
                    logger.info("2-stage verifier blocked response for query: %.80s", message)
                    response_text = get_verification_safe_response()
                    route_rule += ":verified_blocked"

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

            # --- 8. Persist exchange ---
            save_chat_to_db(user_id, message, response_text, session_id)

            # --- 9. Post-session summarization check ---
            msg_count = session_memory.get_message_count(session_id)
            if msg_count >= POST_SESSION_SUMMARY_THRESHOLD and msg_count % POST_SESSION_SUMMARY_THRESHOLD == 0:
                logger.info(
                    "Post-session summary trigger: session=%s msg_count=%d threshold=%d",
                    session_id, msg_count, POST_SESSION_SUMMARY_THRESHOLD,
                )
                self._trigger_post_session_summary(user_id, session_id)

            elapsed_ms = int((time.time() - request_start) * 1000)
            logger.info(
                "Chat response generated for %s in %dms (model=%s route=%s)",
                user_name, elapsed_ms, model_id, route_rule,
            )
            return response_text, model_id, route_rule

        except Exception as e:
            logger.error("Error in chat processing: %s", e, exc_info=True)
            return (
                "I apologise, but I encountered an error processing your message. Please try again.",
                model_id,
                "error_fallback",
            )

    # ------------------------------------------------------------------
    # Fallback to v2 router
    # ------------------------------------------------------------------
    def _fallback_to_v2(self, message: str, session_id: str) -> str:
        """Use v2 router as fallback when v3 is unavailable."""
        router_pick = "llama-3.3-70b-versatile"
        try:
            from routing.model_router_v2 import get_best_model as get_best_model_v2
            import asyncio
            try:
                asyncio.get_running_loop()
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
        return router_pick

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
    # Research-augmented response generation
    # ------------------------------------------------------------------
    def _generate_research_response(
        self,
        message: str,
        system_prompt: str,
        context_messages: List[Dict[str, str]],
        model_id: str,
        research_context: str,
        session_id: str,
    ) -> str:
        """Generate a response with research context injected.

        Structures the prompt per spec:
          User Question → Research Context → Conversation Memory → Instructions
        """
        # Build memory context from conversation history
        research_system_prompt = system_prompt + "\n\n" + _LIVE_RESEARCH_SYSTEM_OVERRIDE

        memory_parts: List[str] = []
        for m in context_messages:
            if m["role"] == "system":
                continue
            if m["role"] == "user":
                memory_parts.append(f"User: {m['content']}")
            elif m["role"] == "assistant":
                memory_parts.append(f"Assistant: {m['content']}")
        memory_context = "\n".join(memory_parts[-10:])  # last 10 turns

        # Structured research prompt
        research_prompt_parts = [
            f"User Question:\n{message}",
            f"Research Context:\n{research_context}",
        ]
        if memory_context:
            research_prompt_parts.append(f"Conversation Memory:\n{memory_context}")
        research_prompt_parts.append(
            "Instructions:\n"
            "Use the research information if relevant. "
            "Combine it with the conversation context to produce a clear answer. "
            "The user already enabled browser search for this turn, so do not tell them to enable search again. "
            "If the research context answers the question, answer directly instead of giving a generic recency warning."
        )
        research_prompt = "\n\n".join(research_prompt_parts)

        # Try orchestrator first, then direct Groq
        if ORCHESTRATOR_AVAILABLE:
            try:
                import asyncio
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            llm_orchestrate(
                                user_message=research_prompt,
                                system_prompt=research_system_prompt,
                                memory_context=None,
                                developer_forced_model=model_id,
                                session_id=session_id,
                            )
                        )
                        reply = result.get("reply", "")
                        if reply:
                            sanitized = _strip_redundant_search_warning(sanitize_response(reply))
                            is_valid, _ = validate_response(sanitized, None)
                            if is_valid:
                                return sanitized
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
            except Exception as e:
                logger.warning("Orchestrator failed for research response: %s", e)

        # Direct Groq fallback
        try:
            response = self.groq_client.generate_content(
                prompt=research_prompt,
                system_instruction=research_system_prompt,
                model_id=model_id,
            )
            if response:
                return _strip_redundant_search_warning(sanitize_response(response))
        except Exception as e:
            logger.error("Direct Groq research generation failed: %s", e)

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
if os.getenv("DISABLE_MEMORY_INIT") == "1":
    class _DummyChatManager:
        def chat_with_memory(self, *args, **kwargs):
            raise RuntimeError("ChatManager is disabled when DISABLE_MEMORY_INIT=1")

    chat_manager = _DummyChatManager()
    logger.info("Using dummy chat manager (DISABLE_MEMORY_INIT=1)")
else:
    chat_manager = ChatManager()


def chat_with_memory(
    user_id: str,
    message: str,
    session_id: Optional[str] = None,
    top_k: int = 5,
    search_mode: bool = False,
    skill: str = "auto",
) -> Tuple[str, str, str]:
    """Backward-compatible function wrapper."""
    return chat_manager.chat_with_memory(
        user_id=user_id,
        message=message,
        session_id=session_id,
        top_k=top_k,
        search_mode=search_mode,
        skill=skill,
    )
