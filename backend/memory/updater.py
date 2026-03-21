from datetime import datetime
from llm.router import LLMRouter
from db.mongo import insert_memory, find_similar_memory, update_memory

class MemoryUpdater:
    def __init__(self):
        self.llm = LLMRouter().get_model("mid")

    async def process(self, user_id, user_input, assistant_response):
        extracted = await self.extract_memory(user_input, assistant_response)

        for mem_type, items in extracted.items():
            for content in items:
                importance = await self.score_importance(content)

                memory = {
                    "user_id": user_id,
                    "type": mem_type,
                    "content": content,
                    "importance": importance,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                await self._upsert(memory)

    async def extract_memory(self, user_input, response):
        prompt = f"""
        Extract memory from the following conversation.

        Return JSON:
        {{
            "facts": ["..."],
            "preferences": ["..."],
            "events": ["..."]
        }}

        Conversation:
        User: {user_input}
        Assistant: {response}
        """

        result = await self.llm.generate(prompt)

        try:
            import json
            text = result.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except:
            return {"facts": [], "preferences": [], "events": []}

    async def score_importance(self, content):
        prompt = f"""
        Rate importance (1-10) of the following memory fact:
        "{content}"
        Return ONLY the integer.
        """

        result = await self.llm.generate(prompt)

        try:
            return float(result.strip())
        except:
            return 5.0

    async def resolve_conflict(self, old_content, new_content):
        prompt = f"""
        Resolve conflict between these two related memories. Keep the most up-to-date and accurate information. Combine them if they are both valid but slightly different aspects.
        
        Old: {old_content}
        New: {new_content}

        Return ONLY the best unified version of the memory.
        """
        
        return await self.llm.generate(prompt)

    async def _upsert(self, new_memory):
        # Apply decay to existing before finding similarities / resolving
        # Assuming find_similar_memory returns dict or None
        existing = find_similar_memory(content=new_memory["content"], user_id=new_memory["user_id"])

        if existing:
            merged_content = await self.resolve_conflict(existing["content"], new_memory["content"])
            
            # Apply time-based decay 
            days_old = (datetime.utcnow() - existing.get("updated_at", existing.get("created_at", datetime.utcnow()))).days
            existing_decayed_importance = existing.get("importance", 5) * (0.98 ** days_old)
            
            # Reinforcement + combination
            new_importance = max(existing_decayed_importance, new_memory["importance"]) + 1

            update_memory(existing["_id"], {
                "content": merged_content,
                "importance": new_importance,
                "updated_at": datetime.utcnow()
            })
        else:
            insert_memory(new_memory)
