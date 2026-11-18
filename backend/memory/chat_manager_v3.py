from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Union, Optional

from memory.controller import MemoryController
from memory.retriever import MemoryRetriever
from memory.updater import MemoryUpdater
from llm.router import LLMRouter
from llm.prompts import PromptBuilder
from llm.errors import LLMProviderError
from config.active_models import get_role_model


logger = logging.getLogger(__name__)


class ChatManagerV3:
    def __init__(self):
        self.memory_retriever = MemoryRetriever()
        self.memory_updater = MemoryUpdater()
        self.llm_router = LLMRouter()
        self.memory_controller = MemoryController(llm_client=self.llm_router.get_model("fast"))
        self.prompt_builder = PromptBuilder()
        self._recent_responses: Dict[str, List[str]] = {}

    async def handle_chat(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        chat_history: List[Dict[str, str]],
        skill: str = "auto",
        search_mode: bool = False,
    ) -> Dict[str, Any]:
        # 1. INTENT ANALYSIS (best-effort; do not fail the chat turn)
        try:
            intent_data = await self._analyze_intent(user_input)
        except Exception as exc:
            logger.warning("Intent analysis failed; using defaults: %s", exc)
            intent_data = {"intent": "general", "needs_memory": False, "memory_types": []}

        # 2. MEMORY DECISION (best-effort)
        try:
            decision = await self.memory_controller.decide(intent_data, user_input)
        except Exception as exc:
            logger.warning("Memory decision failed; skipping retrieval: %s", exc)
            decision = {"use_memory": False, "types": [], "top_k": 0}

        use_memory = decision.get("use_memory", False)
        memory_types = decision.get("types", [])
        top_k = decision.get("top_k", 5)

        # 3–4. MEMORY RETRIEVAL + RERANK (best-effort)
        retrieved_memories = []
        if use_memory and memory_types:
            try:
                retrieved_memories = await self.memory_retriever.retrieve(
                    user_id=user_id,
                    query=user_input,
                    memory_types=memory_types,
                    top_k=min(top_k * 4, 20),
                )
                retrieved_memories = await self.memory_retriever.rerank(
                    query=user_input,
                    memories=retrieved_memories,
                    top_k=5,
                )
                self.memory_updater.reinforce_memories(retrieved_memories, user_id)
            except Exception as exc:
                logger.warning("Memory retrieval failed; continuing without memories: %s", exc)
                retrieved_memories = []

        logger.debug("INTENT: %s", intent_data)
        logger.debug("MEMORIES: %s", retrieved_memories)

        # 5. SKILL RESOLUTION & LIVE WEB SEARCH
        active_skill = None
        try:
            from skills.skill_manager import skill_manager
            active_skill = skill_manager.resolve_skill(skill, user_input)
            if active_skill:
                logger.info("Active skill resolved: %s (mode=%s)", active_skill.name, skill)
        except Exception as skill_err:
            logger.warning("Skill resolution failed: %s", skill_err)

        search_results = None
        suggest_search = False
        try:
            from tools.web_search import search_web, detect_search_need
            needs_search = detect_search_need(user_input)
            import re
            explicit_search_cmd = bool(re.search(r"\b(search\s+(the\s+)?(web|internet|google)|look\s+up\s+online)\b", user_input, re.IGNORECASE))

            if search_mode or explicit_search_cmd:
                logger.info("Executing web search for query: '%s' (forced=%s)", user_input, search_mode)
                search_results = await search_web(user_input, max_results=5)
            elif needs_search:
                suggest_search = True
        except Exception as search_err:
            logger.warning("Web search lookup failed: %s", search_err)

        # 6. FETCH USER PROFILE & BUILD PROMPT
        user_profile = None
        core_facts = []
        try:
            from memory.user_profile import get_user_profile
            user_profile = get_user_profile(user_id)
        except Exception as prof_err:
            logger.debug("Could not load user profile for %s: %s", user_id, prof_err)

        try:
            from db.mongo import get_active_user_facts
            core_facts = get_active_user_facts(user_id, limit=8)
        except Exception as facts_err:
            logger.debug("Could not load active facts for %s: %s", user_id, facts_err)

        prompt = self.prompt_builder.build(
            user_input=user_input,
            chat_history=chat_history,
            memories=retrieved_memories,
            user_profile=user_profile,
            core_facts=core_facts,
            active_skill=active_skill,
            search_results=search_results,
        )
        style_intent = self._normalize_style_intent(intent_data, user_input, active_skill=active_skill)
        model_type = self._model_type_for_style_intent(style_intent)
        styled_prompt = self._apply_turn_style(prompt, user_input, intent_data)
        model_id = get_role_model(model_type)

        # 7. GENERATE RESPONSE — provider failures must propagate
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
            try:
                varied = await self._generate_response(variation_prompt, model_type=model_type)
                response = self._normalize_response(varied)
                response = self._polish_length(response, user_input)
            except LLMProviderError:
                # Keep the first successful response rather than failing the turn.
                logger.warning("Variation regeneration failed; keeping original response")

        if not response or not str(response).strip():
            raise LLMProviderError("Empty model response", model=model_id, status_code=502)

        self._store_response(user_id, response)

        # 8. UPDATE MEMORY (ASYNC) — failures are logged, never persisted as chat
        task = asyncio.create_task(
            self.memory_updater.process(
                user_id=user_id,
                user_input=user_input,
                assistant_response=response,
            )
        )
        task.add_done_callback(self._on_updater_done)

        logger.debug("FINAL RESPONSE: %s", response)
        return {
            "reply": response,
            "model": model_id,
            "route_rule": f"v3_{model_type}",
            "session_id": session_id,
            "active_skill": active_skill.id if active_skill else "auto",
            "search_mode": search_mode,
            "search_results": search_results,
            "suggest_search": suggest_search,
        }

    # =====================================================
    # INTERNAL METHODS
    # =====================================================

    async def _analyze_intent(self, user_input: str) -> Dict:
        clean_text = (user_input or "").strip()
        words = clean_text.split()

        # Fast path 1: Explicit recall phrases -> immediate memory intent
        from memory.controller import RECALL_PATTERNS
        if any(pat.search(clean_text) for pat in RECALL_PATTERNS):
            return {
                "intent": "personal",
                "needs_memory": True,
                "memory_types": ["fact", "preference", "event", "session_summary"],
            }

        # Fast path 2: Short casual banter -> general intent, no memory needed
        if len(words) <= 3 and any(w.lower() in {"hi", "hello", "hey", "sup", "yo", "morning", "thanks", "ok", "cool"} for w in words):
            return {
                "intent": "casual",
                "needs_memory": False,
                "memory_types": [],
            }

        # Fast path 3: Context-rich natural queries -> immediate memory-enabled intent without LLM latency
        query = clean_text.lower()
        if any(w in query for w in {"code", "coding", "programming", "debug", "bug", "refactor", "function", "api", "script", "rust", "tokio", "redis", "queue"}):
            return {
                "intent": "code",
                "needs_memory": True,
                "memory_types": ["fact", "preference", "event"],
            }
        if any(w in query for w in {"trail", "trails", "park", "dog", "walk", "trip", "travel", "vacation", "run", "running", "marathon", "diet", "coffee", "tea", "drink", "book", "read", "camera", "lens", "hike"}):
            return {
                "intent": "personal",
                "needs_memory": True,
                "memory_types": ["fact", "preference", "event", "session_summary"],
            }

        prompt = f"""
        Classify user intent.

        Return JSON:
        {{
            "intent": "...",
            "needs_memory": true/false,
            "memory_types": ["fact", "event", "preference"]
        }}

        User Input:
        {user_input}
        """

        model = self.llm_router.get_model("fast")
        result = await model.generate(prompt)
        return self._safe_json_parse(result)

    async def _generate_response(self, prompt: str, model_type: str = "main") -> str:
        model = self.llm_router.get_model(model_type)
        return await model.generate(prompt)

    def _normalize_response(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        return "\n\n".join(part.strip() for part in cleaned.split("\n\n") if part.strip())

    def _apply_turn_style(self, base_prompt: str, user_input: str, intent_data: Dict[str, Any]) -> str:
        words = (user_input or "").strip().split()
        word_count = len(words)
        style_intent = self._normalize_style_intent(intent_data, user_input)

        if style_intent == "code":
            style_hint = (
                "Response style for this turn:\n"
                "- Use a clear code-support format: short diagnosis, then fix/solution.\n"
                "- Include numbered steps for debugging or implementation tasks.\n"
                "- Keep explanations practical and concrete."
            )
        elif style_intent == "reasoning":
            style_hint = (
                "Response style for this turn:\n"
                "- Use structured reasoning with clear numbered steps.\n"
                "- State assumptions briefly when needed.\n"
                "- End with a concise final takeaway."
            )
        elif style_intent == "summarization":
            style_hint = (
                "Response style for this turn:\n"
                "- Start with a brief key takeaway.\n"
                "- Use compact bullet points for core details.\n"
                "- Keep it concise and easy to skim."
            )
        elif word_count <= 6:
            style_hint = (
                "Response style for this turn:\n"
                "- Keep it short: 1-3 sentences.\n"
                "- Friendly, natural, and direct.\n"
                "- No long preamble."
            )
        elif word_count <= 25:
            style_hint = (
                "Response style for this turn:\n"
                "- Keep it medium length and easy to scan.\n"
                "- Use a warm tone and practical wording.\n"
                "- Add brief structure only if it improves clarity."
            )
        else:
            style_hint = (
                "Response style for this turn:\n"
                "- Provide a structured response with clear sections or bullets if helpful.\n"
                "- Keep a friendly tone while being detailed and specific.\n"
                "- End with a clear next step when appropriate."
            )

        return f"{base_prompt}\n\n{style_hint}"

    def _normalize_style_intent(
        self,
        intent_data: Dict[str, Any],
        user_input: str,
        active_skill: Optional[Any] = None,
    ) -> str:
        if active_skill:
            skill_id = getattr(active_skill, "id", "")
            if skill_id == "code":
                return "code"
            elif skill_id == "problem":
                return "reasoning"
            elif skill_id == "summarizing":
                return "summarization"

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

    def _safe_json_parse(self, text: str) -> Dict:
        import json

        try:
            cleaned = (text or "").strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.replace("```json", "", 1)
            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```", "", 1)
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            data = json.loads(cleaned.strip())
            if not isinstance(data, dict):
                raise ValueError("Invalid intent payload format")

            memory_types = data.get("memory_types", [])
            if not isinstance(memory_types, list):
                memory_types = []

            normalized_types = []
            for t in memory_types:
                if not isinstance(t, str):
                    continue
                ts = t.strip().lower()
                if ts in ("fact", "facts"):
                    normalized_types.append("fact")
                elif ts in ("preference", "preferences"):
                    normalized_types.append("preference")
                elif ts in ("event", "events"):
                    normalized_types.append("event")

            return {
                "intent": data.get("intent", "general"),
                "needs_memory": bool(data.get("needs_memory", False)),
                "memory_types": list(dict.fromkeys(normalized_types)),
            }
        except Exception:
            return {
                "intent": "general",
                "needs_memory": False,
                "memory_types": []
            }

    def _on_updater_done(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception as exc:
            logger.error("Memory updater background task failed: %s", exc, exc_info=True)
