from typing import List, Dict, Any, Optional
from db.pinecone import query_vectors


class MemoryRetriever:
    def __init__(self, llm_client=None):
        self._llm = llm_client

    @property
    def llm(self):
        if self._llm is None:
            try:
                from llm.router import LLMRouter
                self._llm = LLMRouter().get_model("mid")
            except Exception:
                self._llm = None
        return self._llm

    async def retrieve(self, user_id: str, query: str, memory_types: List[str], top_k: int = 20) -> List[Dict[str, Any]]:
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
            if r.get("text") and str(r.get("text")).strip()
        ]

        def _relevance_score(m):
            sim = max(0.0, min(1.0, float(m["score"])))
            raw_imp = float(m["metadata"].get("importance", 5.0) or 5.0)
            norm_imp = (raw_imp / 10.0) if raw_imp > 1.0 else max(0.0, min(1.0, raw_imp))
            return (sim * 0.80) + (norm_imp * 0.20)

        memories.sort(key=_relevance_score, reverse=True)
        return memories[:top_k]

    async def rerank(self, query: str, memories: List[Dict[str, Any]], top_k: int = 5, use_llm: bool = False) -> List[Dict[str, Any]]:
        if not memories:
            return []

        # Optional LLM reranking path
        if use_llm and self.llm:
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
                if isinstance(ranked, list):
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
                    if valid:
                        valid = sorted(valid, key=lambda x: x["score"], reverse=True)
                        return [memories[v["index"]] for v in valid[:top_k]]
            except Exception:
                pass

        # Fast, deterministic hybrid reranker (Cosine Similarity + Importance + Lexical Overlap)
        query_words = set(query.lower().split())
        def _score(m):
            sim = max(0.0, min(1.0, float(m.get("score", 0.0) or 0.0)))
            raw_imp = float(m.get("metadata", {}).get("importance", 5.0) or 5.0)
            norm_imp = (raw_imp / 10.0) if raw_imp > 1.0 else max(0.0, min(1.0, raw_imp))
            text_words = set(m.get("text", "").lower().split())
            overlap = len(query_words & text_words) / max(len(query_words), 1) if query_words else 0.0
            return (sim * 0.70) + (norm_imp * 0.20) + (min(overlap, 1.0) * 0.10)

        sorted_memories = sorted(memories, key=_score, reverse=True)
        return sorted_memories[:top_k]
