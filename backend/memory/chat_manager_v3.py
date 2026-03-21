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

        print("INTENT:", intent_data)
        print("MEMORIES:", retrieved_memories)

        # -----------------------------
        # 5. BUILD PROMPT
        # -----------------------------
        prompt = self.prompt_builder.build(
            user_input=user_input,
            chat_history=chat_history,
            memories=retrieved_memories,
        )

        # -----------------------------
        # 6. GENERATE RESPONSE
        # -----------------------------
        response = await self._generate_response(prompt)

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

        print("FINAL RESPONSE:", response)
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

    async def _generate_response(self, prompt: str) -> str:
        model = self.llm_router.get_model("main")
        return await model.generate(prompt)

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
