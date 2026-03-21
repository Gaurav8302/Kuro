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
        memories = [
            {
                "text": r.get("text", ""),
                "score": float(r.get("score", 0.0) or 0.0),
                "metadata": r.get("metadata", {}) or {},
            }
            for r in results
        ]

        memories = [m for m in memories if float(m["metadata"].get("importance", 0) or 0) > 3]
        memories.sort(
            key=lambda x: (
                x["score"] * 0.7 + float(x["metadata"].get("importance", 5) or 5) * 0.3
            ),
            reverse=True,
        )
        return memories[:top_k]

    async def rerank(self, query, memories, top_k=5):
        if not memories:
            return []

        try:
            import json
            indexed_memories = [
                {"index": idx, "text": m.get("text", "")}
                for idx, m in enumerate(memories)
            ]

            prompt = f"""
            Rank these memories by relevance to the query.
            Return JSON:
            [
              {{"index": int, "score": float}}
            ]

            Query: {query}
            Memories: {indexed_memories}
            """

            response = await self.llm.generate(prompt)
            text = (response or "").strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]

            ranked = json.loads(text.strip())
            if not isinstance(ranked, list):
                raise ValueError("Invalid reranker payload")

            valid = []
            for item in ranked:
                if not isinstance(item, dict):
                    continue
                idx = item.get("index")
                score = item.get("score")
                if isinstance(idx, int) and 0 <= idx < len(memories):
                    try:
                        valid.append({"index": idx, "score": float(score)})
                    except Exception:
                        continue

            valid = sorted(valid, key=lambda x: x["score"], reverse=True)
            return [memories[v["index"]] for v in valid[:top_k]]
        except Exception:
            return memories[:top_k]
