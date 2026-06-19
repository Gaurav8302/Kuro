import asyncio
import logging
import re
from typing import Any, Awaitable, Callable, List, Dict, Optional

from memory.controller import MemoryController
from memory.retriever import MemoryRetriever
from memory.updater import MemoryUpdater
from memory.context_assembler import ContextAssembler
from llm.router import LLMRouter
from skills.router import SkillRouter
from core.hooks import HookPoint, get_hook_registry
from core.events import event_bus, Event
from retrieval import get_rag_pipeline, rag_retrieval_enabled


logger = logging.getLogger(__name__)

# Default system prompt for Kuro
_SYSTEM_PROMPT = (
    "You are Kuro, a friendly conversational AI.\n"
    "- NEVER output JSON.\n"
    "- Always respond naturally in plain language.\n"
    "- Keep a warm, human tone without sounding overly formal.\n"
    "- Avoid repetitive opening lines and avoid reusing the same sentence patterns turn after turn.\n"
    "- Prefer specific, useful responses over generic filler.\n"
    "- If the user message is short or casual, keep your response concise and friendly."
)

# Keyword sets for intent detection
_PERSONAL_KW = frozenset({
    "my name", "i am", "i'm", "i like", "i prefer", "i love",
    "i hate", "i want", "my favorite", "remember that", "do you remember",
    "did i tell you", "i told you", "about me", "my birthday",
    "i live", "my hobby", "i work", "my job", "my email",
})
_RECALL_KW = frozenset({
    "do you remember", "did i tell", "what did i say",
    "what do you know about me", "recall", "what is my",
    "what's my", "you told me", "we talked about",
    "last time", "previously", "before",
})
_CODE_KW = frozenset({
    "code", "function", "debug", "bug", "error", "script",
    "python", "javascript", "typescript", "api", "refactor",
    "implement", "class", "method", "variable", "compile",
    "traceback", "exception", "syntax", "algorithm",
})
_REASONING_KW = frozenset({
    "why", "how does", "explain", "compare", "difference",
    "pros and cons", "analyze", "reason", "logic", "math",
    "calculate", "equation", "derive", "prove", "optimize",
})
_GREETING_KW = frozenset({
    "hi", "hello", "hey", "sup", "yo", "good morning",
    "good evening", "good night", "howdy", "what's up",
    "how are you", "how's it going",
})
_CREATIVE_KW = frozenset({
    "write a story", "poem", "creative", "imagine", "fiction",
    "song", "lyrics", "narrative",
})

_CODE_RE = re.compile(r"```|def |class |import |function\s|const |let |var ")


class ChatManagerV3:
    def __init__(self):
        self.memory_retriever = MemoryRetriever()
        self.memory_updater = MemoryUpdater()
        self.llm_router = LLMRouter()
        self.memory_controller = MemoryController()
        self.context_assembler = ContextAssembler()
        self.skill_router = SkillRouter()
        self.hooks = get_hook_registry()
        self._recent_responses: Dict[str, List[str]] = {}

    async def handle_chat(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        chat_history: List[Dict[str, str]],
        insight_hook: Optional[
            Callable[[str, str, List[Dict[str, Any]]], Awaitable[List[Dict[str, str]]]]
        ] = None,
    ) -> Dict[str, Any]:

        # -----------------------------
        # 0. PRE-CHAT HOOK
        # -----------------------------
        pre_ctx = await self.hooks.execute(HookPoint.PRE_CHAT, {
            "user_id": user_id, "session_id": session_id,
            "user_input": user_input,
        })
        if pre_ctx.abort:
            return {"response": pre_ctx.abort_reason or "Request blocked by safety hook.", "model": "hook", "rule": "pre_chat_hook"}

        # -----------------------------
        # 1. INTENT ANALYSIS
        # -----------------------------
        intent_data = await self._analyze_intent(user_input)

        # -----------------------------
        # 1b. SKILL MATCHING
        # -----------------------------
        matched_skill = self.skill_router.match(user_input, intent=intent_data.get("intent"))
        skill_prompt = ""
        if matched_skill:
            skill_prompt = matched_skill.system_prompt or ""
            self.skill_router.mark_used(matched_skill.name)
            logger.debug("SKILL MATCHED: %s", matched_skill.name)

        # -----------------------------
        # 2. MEMORY DECISION
        # -----------------------------
        decision = await self.memory_controller.decide(intent_data, user_input)
        
        use_memory = decision.get("use_memory", False)
        memory_types = decision.get("types", [])
        top_k = decision.get("top_k", 5)

        # -----------------------------
        # 3. MEMORY RETRIEVAL
        # -----------------------------
        retrieved_memories = []
        rag_context = ""
        insight_entries: List[Dict[str, str]] = []
        if use_memory and memory_types:
            retrieved_memories = await self.memory_retriever.retrieve(
                user_id=user_id,
                query=user_input,
                memory_types=memory_types,
                top_k=min(top_k * 4, 20),
            )

            # -----------------------------
            # 4. MEMORY RERANKING
            # -----------------------------
            retrieved_memories = await self.memory_retriever.rerank(
                query=user_input,
                memories=retrieved_memories,
                top_k=5,
            )
            self.memory_updater.reinforce_memories(retrieved_memories)

            # POST-MEMORY HOOK
            await self.hooks.execute(HookPoint.POST_MEMORY, {
                "user_id": user_id, "memories": retrieved_memories,
            })

            # -----------------------------
            # 4b. OPTIONAL RAG MEMORY (facts + preferences + summaries)
            # -----------------------------
            if rag_retrieval_enabled():
                try:
                    pipeline = get_rag_pipeline()
                    rag_result = pipeline.retrieve(user_input, user_id=user_id)
                    rag_context = rag_result.get("context", "") or ""
                except Exception as rag_err:
                    logger.debug("RAG retrieval failed (non-blocking): %s", rag_err)

            # -----------------------------
            # 4c. INSIGHT RETRIEVAL (meta/decision queries only)
            # -----------------------------
            if insight_hook:
                try:
                    insight_entries = await insight_hook(user_id, user_input, retrieved_memories)
                except Exception as insight_err:
                    logger.debug("Insight hook failed (non-blocking): %s", insight_err)

        logger.debug("INTENT: %s", intent_data)
        logger.debug("MEMORIES: %s", retrieved_memories)

        # -----------------------------
        # 5. BUILD PROMPT (token-aware)
        # -----------------------------
        # Merge system prompt: base + skill-specific
        system_prompt = _SYSTEM_PROMPT
        if skill_prompt:
            system_prompt = f"{_SYSTEM_PROMPT}\n\n{skill_prompt}"
        if rag_context:
            system_prompt = f"{system_prompt}\n\nRelevant memory context:\n{rag_context}"
        if insight_entries:
            insight_text = "\n".join(
                f"• {entry.get('content', '')}" for entry in insight_entries
            )
            system_prompt = (
                f"{system_prompt}\n\n"
                f"Insights about the user:\n{insight_text}"
            )

        style_intent = self._normalize_style_intent(intent_data, user_input)
        model_type = self._model_type_for_style_intent(style_intent)
        style_hint = self._get_style_hint(style_intent, user_input)

        # Look up the actual model name that will be used
        _model_map = {
            "code": "llama-3.1-8b-instant",
            "reasoning": "deepseek-r1-distill-llama-70b",
            "summarization": "mixtral-8x7b-32k",
            "conversation": "llama-3.3-70b-versatile",
        }
        actual_model = _model_map.get(model_type, "llama-3.3-70b-versatile")

        styled_prompt = self.context_assembler.build(
            system_prompt=system_prompt,
            memories=retrieved_memories,
            history=chat_history,
            user_message=user_input,
            style_hint=style_hint,
        )

        # -----------------------------
        # 6. GENERATE RESPONSE
        # -----------------------------
        response = await self._generate_response(styled_prompt, model_type=model_type)
        response = self._normalize_response(response)
        response = self._polish_length(response, user_input)

        if self._is_repetitive_response(user_id, response):
            logger.info("Repetitive response detected in ChatManagerV3; regenerating with variation hint")
            variation_prompt = (
                f"{styled_prompt}\n\n"
                "Additional instruction:\n"
                "- Rephrase with fresh wording and a friendly tone.\n"
                "- Avoid repeating previous opening lines.\n"
                "- Keep the same meaning while sounding natural."
            )
            varied = await self._generate_response(variation_prompt, model_type=model_type)
            response = self._normalize_response(varied)
            response = self._polish_length(response, user_input)

        self._store_response(user_id, response)

        # -----------------------------
        # 7. UPDATE MEMORY (ASYNC)
        # -----------------------------
        task = asyncio.create_task(
            self.memory_updater.process(
                user_id=user_id,
                user_input=user_input,
                assistant_response=response,
            )
        )
        task.add_done_callback(self._on_updater_done)

        # -----------------------------
        # 8. POST-CHAT HOOK + EVENTS
        # -----------------------------
        await self.hooks.execute(HookPoint.POST_CHAT, {
            "user_id": user_id, "session_id": session_id,
            "user_input": user_input, "response": response,
            "intent": intent_data, "skill": matched_skill.name if matched_skill else None,
        })
        await event_bus.emit(Event("chat.responded", {
            "user_id": user_id, "session_id": session_id,
            "intent": intent_data.get("intent"),
        }))

        logger.debug("FINAL RESPONSE: %s (model=%s, rule=%s)", response, actual_model, style_intent)
        return {
            "response": response,
            "model": actual_model,
            "rule": f"skill:{style_intent}",
        }

    # =====================================================
    # INTERNAL METHODS
    # =====================================================

    async def _analyze_intent(self, user_input: str) -> Dict:
        """Rule-based intent classification — zero LLM calls.

        Replaces the previous LLM-driven classifier that added ~500ms
        latency per turn. Uses keyword/regex matching which is both
        faster and more deterministic.
        """
        query = (user_input or "").lower().strip()

        def _has_any(keywords):
            return any(kw in query for kw in keywords)

        # Greeting — no memory needed
        if _has_any(_GREETING_KW) and len(query.split()) <= 8:
            return {"intent": "greeting", "needs_memory": False, "memory_types": []}

        # Personal recall — definitely needs memory
        if _has_any(_RECALL_KW):
            return {
                "intent": "recall",
                "needs_memory": True,
                "memory_types": ["fact", "preference", "event"],
            }

        # Personal information sharing — needs memory for dedup
        if _has_any(_PERSONAL_KW):
            return {
                "intent": "personal",
                "needs_memory": True,
                "memory_types": ["fact", "preference"],
            }

        # Code help (still allow memory if self-referential cues present)
        has_recall_or_personal = _has_any(_RECALL_KW) or _has_any(_PERSONAL_KW)
        if _has_any(_CODE_KW) or _CODE_RE.search(query):
            return {"intent": "code", "needs_memory": has_recall_or_personal, "memory_types": ["fact", "preference", "event"] if has_recall_or_personal else []}

        # Reasoning / analysis (still allow memory if self-referential cues present)
        if _has_any(_REASONING_KW):
            return {"intent": "reasoning", "needs_memory": has_recall_or_personal, "memory_types": ["fact", "preference", "event"] if has_recall_or_personal else []}

        # Creative
        if _has_any(_CREATIVE_KW):
            return {"intent": "creative", "needs_memory": False, "memory_types": []}

        # Default: general conversation — light memory check
        if len(query.split()) > 12:
            return {
                "intent": "general",
                "needs_memory": True,
                "memory_types": ["fact", "preference"],
            }

        return {"intent": "general", "needs_memory": False, "memory_types": []}

    async def _generate_response(self, prompt: str, model_type: str = "main") -> str:
        model = self.llm_router.get_model(model_type)
        return await model.generate(prompt)

    def _normalize_response(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return "I'm here with you. Could you share a little more detail so I can help better?"
        return "\n\n".join(part.strip() for part in cleaned.split("\n\n") if part.strip())

    def _get_style_hint(self, style_intent: str, user_input: str) -> str:
        """Return a style hint string based on intent and message length."""
        words = (user_input or "").strip().split()
        word_count = len(words)

        if style_intent == "code":
            return (
                "Response style for this turn:\n"
                "- Use a clear code-support format: short diagnosis, then fix/solution.\n"
                "- Include numbered steps for debugging or implementation tasks.\n"
                "- Keep explanations practical and concrete."
            )
        elif style_intent == "reasoning":
            return (
                "Response style for this turn:\n"
                "- Use structured reasoning with clear numbered steps.\n"
                "- State assumptions briefly when needed.\n"
                "- End with a concise final takeaway."
            )
        elif style_intent == "summarization":
            return (
                "Response style for this turn:\n"
                "- Start with a brief key takeaway.\n"
                "- Use compact bullet points for core details.\n"
                "- Keep it concise and easy to skim."
            )
        elif word_count <= 6:
            return (
                "Response style for this turn:\n"
                "- Keep it short: 1-3 sentences.\n"
                "- Friendly, natural, and direct.\n"
                "- No long preamble."
            )
        elif word_count <= 25:
            return (
                "Response style for this turn:\n"
                "- Keep it medium length and easy to scan.\n"
                "- Use a warm tone and practical wording.\n"
                "- Add brief structure only if it improves clarity."
            )
        else:
            return (
                "Response style for this turn:\n"
                "- Provide a structured response with clear sections or bullets if helpful.\n"
                "- Keep a friendly tone while being detailed and specific.\n"
                "- End with a clear next step when appropriate."
            )

    def _normalize_style_intent(self, intent_data: Dict[str, Any], user_input: str) -> str:
        raw_intent = str(intent_data.get("intent", "") or "").lower()
        query = (user_input or "").lower()

        # Keep emotionally charged or interpersonal statements in conversation mode.
        conversational_tone_markers = {
            "i don't like", "i dont like", "you are the problem", "youre the problem",
            "i hate", "annoying", "upset", "frustrated", "mad at you"
        }
        if any(marker in query for marker in conversational_tone_markers):
            return "conversation"

        code_markers = {
            "code", "coding", "programming", "debug", "bug", "refactor", "function", "api", "script"
        }
        reasoning_markers = {
            "reasoning", "logic", "math", "analysis", "compare", "decision", "plan",
            "solve", "equation", "proof", "derive", "optimize"
        }
        summary_markers = {
            "summary", "summarize", "explain", "tl;dr", "recap", "overview"
        }

        if any(token in raw_intent for token in code_markers) or any(token in query for token in code_markers):
            return "code"
        if any(token in raw_intent for token in reasoning_markers) or any(token in query for token in reasoning_markers):
            return "reasoning"
        if any(token in raw_intent for token in summary_markers) or any(token in query for token in summary_markers):
            return "summarization"
        return "conversation"

    def _model_type_for_style_intent(self, style_intent: str) -> str:
        if style_intent == "code":
            return "code"
        if style_intent == "reasoning":
            return "reasoning"
        if style_intent == "summarization":
            return "summarization"
        return "conversation"

    def _polish_length(self, response: str, user_input: str) -> str:
        user_words = len((user_input or "").strip().split())
        response_words = len((response or "").strip().split())

        if user_words <= 6 and response_words > 120:
            pieces = [p.strip() for p in response.split(".") if p.strip()]
            if len(pieces) >= 2:
                return f"{pieces[0]}. {pieces[1]}."
            if pieces:
                return f"{pieces[0]}."

        return response

    def _is_repetitive_response(self, user_id: str, response: str) -> bool:
        recent = self._recent_responses.get(user_id, [])
        if not recent:
            return False

        new_words = set((response or "").lower().split())
        if not new_words:
            return False

        for prev in recent:
            prev_words = set(prev.lower().split())
            overlap = len(new_words & prev_words) / max(len(new_words), 1)
            if overlap > 0.82:
                return True
        return False

    def _store_response(self, user_id: str, response: str) -> None:
        if user_id not in self._recent_responses:
            self._recent_responses[user_id] = []
        self._recent_responses[user_id].append(response)
        self._recent_responses[user_id] = self._recent_responses[user_id][-4:]

    def _on_updater_done(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception as exc:
            logger.error("Memory updater background task failed: %s", exc, exc_info=True)
