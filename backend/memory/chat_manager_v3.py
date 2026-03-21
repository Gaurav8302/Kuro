import asyncio
from datetime import datetime
from typing import List, Dict, Any

from memory.controller import MemoryController
from memory.retriever import MemoryRetriever
from memory.updater import MemoryUpdater
from llm.router import LLMRouter
from llm.prompts import PromptBuilder


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
    ) -> Dict[str, Any]:

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
        asyncio.create_task(
            self.memory_updater.process(
                user_id=user_id,
                user_input=user_input,
                assistant_response=response,
            )
        )

        return {
            "response": response,
            "memories_used": retrieved_memories,
            "intent": intent_data,
        }

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
            return json.loads(text)
        except Exception:
            return {
                "intent": "general",
                "needs_memory": False,
                "memory_types": []
            }
