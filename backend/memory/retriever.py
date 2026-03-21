from db.pinecone import query_vectors
from llm.router import LLMRouter


class MemoryRetriever:
    def __init__(self):
        self.llm = LLMRouter().get_model("mid")

    async def retrieve(self, user_id, query, memory_types, top_k=20):
        results = query_vectors(
            query=query,
            user_id=user_id,
            memory_types=memory_types,
            top_k=top_k,
        )
        return results

    async def rerank(self, query, memories, top_k=5):
        if not memories:
            return []

        prompt = f"""
        User Query:
        {query}

        Memories:
        {memories}

        Select top {top_k} most relevant memories.
        Return JSON list.
        """

        response = await self.llm.generate(prompt)

        try:
            import json
            return json.loads(response)
        except:
            return memories[:top_k]
