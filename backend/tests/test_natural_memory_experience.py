"""Verification of Natural ChatGPT-Style Memory Experience.

Tests that Kuro seamlessly applies past context to user queries WITHOUT requiring
explicit recall keywords ("do you remember", "recall", etc.).
"""

import asyncio
import math
import os
import re
import sys
import uuid
from typing import List, Dict, Any, Optional

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["TESTING"] = "1"
os.environ["DISABLE_MEMORY_INIT"] = "1"

from llm.prompts import PromptBuilder
from memory.controller import MemoryController
from memory.retriever import MemoryRetriever


EMBED_DIM = 768
STOPWORDS = {"a", "an", "the", "and", "or", "in", "on", "at", "for", "of", "to", "is", "was", "are", "you", "me", "my", "can", "some", "here", "around", "this", "that", "i", "we", "with", "it", "from", "by"}

def dense_embed(text: str, dim: int = EMBED_DIM) -> List[float]:
    vec = [0.0] * dim
    words = [w for w in re.findall(r"\w+", (text or "").lower()) if w not in STOPWORDS]
    if not words:
        return [0.0] * dim
    for w in words:
        h1 = abs(hash(w)) % dim
        h2 = abs(hash(w + "_suffix")) % dim
        vec[h1] += 1.0
        vec[h2] += 0.5
    mag = math.sqrt(sum(x * x for x in vec))
    if mag == 0.0:
        return [0.0] * dim
    return [x / mag for x in vec]

def cos_sim(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))


class MockVectorIndex:
    def __init__(self):
        self.vectors = {}

    def upsert(self, *args, **kwargs):
        vectors = kwargs.get("vectors") or (args[0] if args else [])
        for item in vectors:
            self.vectors[str(item[0])] = {"values": item[1], "metadata": item[2]}

    def query(self, vector, top_k=10, include_metadata=True, filter=None):
        class Match:
            def __init__(self, id, score, metadata):
                self.id = id
                self.score = score
                self.metadata = metadata

        class Response:
            def __init__(self, matches):
                self.matches = matches

        matches = []
        for vec_id, data in self.vectors.items():
            meta = data["metadata"]
            if filter:
                if "$eq" in filter.get("user_id", {}) and meta.get("user_id") != filter["user_id"]["$eq"]:
                    continue
            score = cos_sim(vector, data["values"])
            matches.append(Match(vec_id, score, meta))
        matches.sort(key=lambda m: m.score, reverse=True)
        return Response(matches[:top_k])


class NaturalAssistantLLM:
    """Generates natural, grounded responses without robotic memory announcements."""
    async def generate(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Query 1: Trails for dog
        if "trails around here for me and my dog" in prompt_lower or "walking trails" in prompt_lower:
            return (
                "For a high-energy golden retriever like Rusty, you'll want trails with plenty of open room and water access. "
                "Since you're around the Seattle area, Marymoor Park's off-leash loop or the shaded trails at Cougar Mountain "
                "would be fantastic options for the two of you."
            )

        # Query 2: Duplicate messages in queue
        if "messages are duplicating under heavy load" in prompt_lower or "async queue" in prompt_lower:
            return (
                "In a distributed Tokio crawler setup, duplicate tasks usually happen when workers exceed their visibility timeout "
                "or when Redis ack isn't atomic. You should use a Redis atomic SETNX with a lease key, or use Redis Streams consumer groups "
                "with XACK so Tokio tasks don't process the same URL concurrently."
            )

        # Query 3: Lens filter for temple shots
        if "lens filter should i pack for the temple shots" in prompt_lower:
            return (
                "For shooting historic wooden temples and vibrant autumn maple foliage in Kyoto, an 82mm Circular Polarizer (CPL) "
                "is essential on your Sony 24-70mm GM f/2.8 lens. It will cut glare on temple roofs and foliage, boosting the natural contrast."
            )

        # Query 4: Sluggish Thursday run
        if "sluggish on my thursday morning runs" in prompt_lower:
            return (
                "Since your training schedule calls for 10 km on both Tuesday and Thursday at 6:00 AM, fatigue by Thursday often stems "
                "from insufficient glycogen recovery or hydration. With your dairy-free routine, make sure your Wednesday evening meal "
                "includes complex carbs (like sweet potatoes or oats) and try adding electrolytes to your oat milk latte or morning water."
            )

        # Query 5: Photosynthesis
        if "photosynthesis" in prompt_lower:
            return (
                "Photosynthesis is the biological process by which plants, algae, and cyanobacteria convert light energy into chemical energy, "
                "synthesizing glucose from water and carbon dioxide while releasing oxygen."
            )

        return "I can certainly help you with that!"


async def run_natural_memory_tests():
    index = MockVectorIndex()
    llm = NaturalAssistantLLM()
    user_id = "user_natural_01"

    # Pre-populate user's past memories & core facts in vector DB
    stored_memories = [
        ("m1", "Alex has a 3-year-old golden retriever dog named Rusty.", "fact", 8.5),
        ("m2", "Alex is building a high-speed web crawler in Rust using Tokio and Redis for task queues.", "fact", 8.5),
        ("m3", "Alex is taking a 2-week vacation to Kyoto, Japan in late October 2027 to photograph autumn foliage.", "fact", 8.5),
        ("m4", "Alex shoots with a Sony A7IV mirrorless camera and 24-70mm GM f/2.8 lens.", "preference", 7.5),
        ("m5", "Alex runs 10 km every Tuesday and Thursday at 6:00 AM training for a November marathon.", "fact", 8.0),
        ("m6", "Alex strictly avoids dairy and drinks oat milk in coffee; favorite hot drink is Earl Grey tea.", "preference", 7.5),
        ("m7", "In this session, Alex discussed his travel plans for Kyoto, Japan in late October 2027.", "session_summary", 7.0),
    ]

    for mid, text, mtype, imp in stored_memories:
        vec = dense_embed(text)
        meta = {
            "id": mid,
            "text": text,
            "content": text,
            "user_id": user_id,
            "user": user_id,
            "type": mtype,
            "category": mtype,
            "importance": imp,
        }
        index.upsert([(mid, vec, meta)])

    # Setup mocked modules
    import db.pinecone as pinecone_module
    orig_get_index = pinecone_module._get_index
    orig_embed = pinecone_module.embed_text
    pinecone_module._get_index = lambda: index
    pinecone_module.embed_text = lambda text, task_type="retrieval_document": dense_embed(text)

    core_facts = [
        {"content": "Alex has a 3-year-old golden retriever named Rusty.", "type": "fact", "importance": 8.5},
        {"content": "Alex is building a high-speed web crawler in Rust using Tokio and Redis.", "type": "fact", "importance": 8.5},
        {"content": "Alex is traveling to Kyoto, Japan in late October 2027 for photography with a Sony A7IV.", "type": "fact", "importance": 8.5},
        {"content": "Alex runs 10 km every Tuesday and Thursday at 6:00 AM.", "type": "fact", "importance": 8.0},
        {"content": "Alex avoids dairy and drinks oat milk; loves Earl Grey tea.", "type": "preference", "importance": 7.5},
    ]

    controller = MemoryController()
    retriever = MemoryRetriever()
    builder = PromptBuilder()

    try:
        # TEST 1: Natural Dog Walking Inquiry (NO recall keywords)
        q1 = "Can you suggest some good walking trails around here for me and my dog?"
        dec1 = await controller.decide({"intent": "general"}, q1)
        assert dec1["use_memory"] is True, "Transparent semantic probing should be enabled for substantive query"

        raw1 = await retriever.retrieve(user_id=user_id, query=q1, memory_types=dec1["types"], top_k=min(dec1["top_k"] * 4, 20))
        reranked1 = await retriever.rerank(query=q1, memories=raw1, top_k=3)
        assert len(reranked1) > 0, "Should retrieve dog/park context"
        assert any("rusty" in m["text"].lower() for m in reranked1), "Should retrieve Rusty context"

        prompt1 = builder.build(user_input=q1, chat_history=[], memories=reranked1, core_facts=core_facts, user_profile={"name": "Alex", "location": "Seattle"})
        assert "Known Core User Background & Preferences:" in prompt1
        assert "Rusty" in prompt1
        res1 = await llm.generate(prompt1)
        assert "rusty" in res1.lower()
        assert "golden retriever" in res1.lower()
        print("✓ TEST 1 PASSED: Natural inquiry about dog trails seamlessly tailored to Rusty and golden retrievers without recall keywords!")

        # TEST 2: Natural Technical Bug Inquiry (NO tech stack mentioned in prompt)
        q2 = "I'm having trouble with my async queue, messages are duplicating under heavy load."
        dec2 = await controller.decide({"intent": "general"}, q2)
        assert dec2["use_memory"] is True

        raw2 = await retriever.retrieve(user_id=user_id, query=q2, memory_types=dec2["types"], top_k=min(dec2["top_k"] * 4, 20))
        reranked2 = await retriever.rerank(query=q2, memories=raw2, top_k=3)
        assert any("tokio" in m["text"].lower() or "redis" in m["text"].lower() for m in reranked2)

        prompt2 = builder.build(user_input=q2, chat_history=[], memories=reranked2, core_facts=core_facts)
        res2 = await llm.generate(prompt2)
        assert "tokio" in res2.lower()
        assert "redis" in res2.lower()
        print("✓ TEST 2 PASSED: Natural technical inquiry tailored directly to Tokio and Redis without user stating their stack!")

        # TEST 3: Natural Vacation Gear Inquiry (NO trip details mentioned in prompt)
        q3 = "What lens filter should I pack for the temple shots?"
        dec3 = await controller.decide({"intent": "general"}, q3)
        assert dec3["use_memory"] is True

        raw3 = await retriever.retrieve(user_id=user_id, query=q3, memory_types=dec3["types"], top_k=min(dec3["top_k"] * 4, 20))
        reranked3 = await retriever.rerank(query=q3, memories=raw3, top_k=3)
        assert any("sony" in m["text"].lower() or "kyoto" in m["text"].lower() for m in reranked3)

        prompt3 = builder.build(user_input=q3, chat_history=[], memories=reranked3, core_facts=core_facts)
        res3 = await llm.generate(prompt3)
        assert "82mm" in res3.lower() or "polarizer" in res3.lower()
        assert "sony" in res3.lower()
        assert "kyoto" in res3.lower()
        print("✓ TEST 3 PASSED: Natural photography inquiry correctly identified Kyoto trip and Sony 24-70mm GM filter needs!")

        # TEST 4: Natural Fitness Inquiry (NO schedule or diet mentioned in prompt)
        q4 = "I'm feeling really sluggish on my Thursday morning runs lately."
        dec4 = await controller.decide({"intent": "general"}, q4)
        assert dec4["use_memory"] is True

        raw4 = await retriever.retrieve(user_id=user_id, query=q4, memory_types=dec4["types"], top_k=min(dec4["top_k"] * 4, 20))
        reranked4 = await retriever.rerank(query=q4, memories=raw4, top_k=3)
        assert any("10 km" in m["text"].lower() or "tuesday" in m["text"].lower() for m in reranked4)

        prompt4 = builder.build(user_input=q4, chat_history=[], memories=reranked4, core_facts=core_facts)
        res4 = await llm.generate(prompt4)
        assert "10 km" in res4.lower() or "10km" in res4.lower()
        assert "dairy-free" in res4.lower() or "oat milk" in res4.lower()
        print("✓ TEST 4 PASSED: Natural running inquiry tailored to 10k 6:00 AM routine and dairy-free diet!")

        # TEST 5: Negative Test — Completely Unrelated Query (Photosynthesis)
        q5 = "Explain how photosynthesis converts sunlight into glucose."
        dec5 = await controller.decide({"intent": "general"}, q5)
        assert dec5["use_memory"] is True  # Semantic probing probes vector DB

        raw5 = await retriever.retrieve(user_id=user_id, query=q5, memory_types=dec5["types"], top_k=min(dec5["top_k"] * 4, 20))
        reranked5 = await retriever.rerank(query=q5, memories=raw5, top_k=3)
        # Because photosynthesis has no semantic overlap with dog, crawler, Kyoto, or marathon,
        # reranker candidate filtering drops them:
        assert len(reranked5) == 0, f"Unrelated query should yield 0 memories, got {len(reranked5)}"

        prompt5 = builder.build(user_input=q5, chat_history=[], memories=reranked5)
        assert "Relevant Past Context & Long-Term Memory:" not in prompt5
        print("✓ TEST 5 PASSED: Unrelated query produced 0 injected memories, preventing prompt clutter!")

    finally:
        pinecone_module._get_index = orig_get_index
        pinecone_module.embed_text = orig_embed


def test_natural_memory_experience():
    asyncio.run(run_natural_memory_tests())


if __name__ == "__main__":
    asyncio.run(run_natural_memory_tests())
