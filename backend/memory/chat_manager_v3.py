import asyncio
import logging
from typing import List, Dict, Any

from memory.controller import MemoryController
from memory.retriever import MemoryRetriever
from memory.updater import MemoryUpdater
from llm.router import LLMRouter
from llm.prompts import PromptBuilder


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
    ) -> str:

        # -----------------------------
        # 1. INTENT ANALYSIS
        # -----------------------------
        intent_data = await self._analyze_intent(user_input)

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

        logger.debug("INTENT: %s", intent_data)
        logger.debug("MEMORIES: %s", retrieved_memories)

        # -----------------------------
        # 5. BUILD PROMPT
        # -----------------------------
        prompt = self.prompt_builder.build(
            user_input=user_input,
            chat_history=chat_history,
            memories=retrieved_memories,
        )
        style_intent = self._normalize_style_intent(intent_data, user_input)
        model_type = self._model_type_for_style_intent(style_intent)
        styled_prompt = self._apply_turn_style(prompt, user_input, intent_data)

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

        logger.debug("FINAL RESPONSE: %s", response)
        return response

    # =====================================================
    # INTERNAL METHODS
    # =====================================================

    async def _analyze_intent(self, user_input: str) -> Dict:
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
            return "I'm here with you. Could you share a little more detail so I can help better?"
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
