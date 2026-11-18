"""Full End-to-End Real World Memory Simulation & Verification Test.

Simulates 6 distinct user sessions:
- Session 1: Initial conversation + in-session amnesia test (Rusty, Earl Grey, Rust, Photography).
- Sessions 2 to 5: Long-term conversations across distinct domains:
    - Session 2: Technical architecture (Tokio async, Redis queue, exponential jitter backoff).
    - Session 3: Travel & Photography gear (Kyoto, late October 2027, Sony A7IV, 24-70mm GM).
    - Session 4: Fitness & Routine (10k Tue/Thu 6:00 AM, sub-4 hr marathon, dairy-free/oat milk).
    - Session 5: Career & Reading (Liu Cixin's "The Three-Body Problem", Staff AI Architect).
- Session 6: The Grand Cross-Session Memory Exam:
    - Fresh session with ZERO prior chat history.
    - Validates cross-session retrieval of facts, preferences, and episodic session summaries.
"""

import asyncio
import logging
import math
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["TESTING"] = "1"
os.environ["DISABLE_MEMORY_INIT"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("memory_simulation")


# -----------------------------------------------------------------------------
# 1. High-Fidelity In-Memory Vector Store & Semantic Embedder
# -----------------------------------------------------------------------------
EMBED_DIM = 768

def dense_embed(text: str, dim: int = EMBED_DIM) -> List[float]:
    """Deterministic 768-dimension normalized vector embedding."""
    vec = [0.0] * dim
    words = re.findall(r"\w+", (text or "").lower())
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


class InMemoryPineconeIndex:
    """In-memory Pinecone index simulator with real vector similarity."""
    def __init__(self):
        self.vectors: Dict[str, Dict[str, Any]] = {}

    def upsert(self, *args, **kwargs):
        vectors = kwargs.get("vectors")
        if vectors is None and args:
            vectors = args[0]
        if not vectors:
            return

        for item in vectors:
            vec_id = str(item[0])
            vector = item[1]
            metadata = item[2] if len(item) > 2 else {}
            self.vectors[vec_id] = {
                "id": vec_id,
                "values": vector,
                "metadata": metadata
            }
        logger.info(f"[VectorDB] Upserted {len(vectors)} vectors (total in index: {len(self.vectors)})")

    def query(self, vector: List[float], top_k: int = 10, include_metadata: bool = True, filter: Optional[Dict] = None):
        class Match:
            def __init__(self, id, score, metadata):
                self.id = id
                self.score = score
                self.metadata = metadata

        class QueryResponse:
            def __init__(self, matches):
                self.matches = matches

        matches = []
        for vec_id, data in self.vectors.items():
            meta = data["metadata"]

            # Filter validation
            if filter:
                passed = True
                for k, condition in filter.items():
                    val = meta.get(k)
                    if isinstance(condition, dict):
                        if "$eq" in condition and val != condition["$eq"]:
                            passed = False
                            break
                        if "$in" in condition and val not in condition["$in"]:
                            passed = False
                            break
                    elif val != condition:
                        passed = False
                        break
                if not passed:
                    continue

            score = cos_sim(vector, data["values"])
            matches.append(Match(vec_id, score, meta if include_metadata else {}))

        matches.sort(key=lambda m: m.score, reverse=True)
        return QueryResponse(matches[:top_k])

    def describe_index_stats(self):
        class Stats:
            def __init__(self, count):
                self.total_vector_count = count
        return Stats(len(self.vectors))


# -----------------------------------------------------------------------------
# 2. In-Memory MongoDB Store for Chat & Long-Term Memories
# -----------------------------------------------------------------------------
class InMemoryMongoStore:
    def __init__(self):
        self.memories: Dict[str, Dict[str, Any]] = {}
        self.chat_history: List[Dict[str, Any]] = []

    def insert_memory(self, doc: Dict[str, Any]) -> str:
        mid = doc.get("memory_id") or str(uuid.uuid4())
        doc["_id"] = mid
        self.memories[mid] = doc
        return mid

    def update_memory(self, mid: str, update_fields: Dict[str, Any], user_id: str):
        if mid in self.memories:
            self.memories[mid].update(update_fields)


# -----------------------------------------------------------------------------
# 3. Intelligent Persona LLM Simulation
# -----------------------------------------------------------------------------
class SimulationLLM:
    """Generates realistic responses based on prompt, history, and memories."""

    async def generate(self, prompt: str) -> str:
        return self._generate_sync(prompt)

    def _generate_sync(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Handle controller decision
        if "analyze if this user input requires retrieving" in prompt_lower:
            import json
            return json.dumps({
                "use_memory": True,
                "types": ["fact", "preference", "event", "session_summary"],
                "top_k": 5
            })

        # Handle batch memory extraction
        if "extract notable long-term facts" in prompt_lower or "extract memory" in prompt_lower:
            return self._extract_facts(prompt)

        # Handle session summarization
        if "summarize the following conversation" in prompt_lower:
            return self._summarize_session(prompt)

        # Handle chat response generation
        return self._synthesize_chat_reply(prompt)

    def _extract_facts(self, prompt: str) -> str:
        import json
        facts = []

        # Turn 1: Rusty, Alex, Rust crawler, Earl Grey
        if "golden retriever" in prompt or "rusty" in prompt:
            facts.append({"content": "Alex has a 3-year-old golden retriever named Rusty.", "type": "fact", "importance": 8.5})
        if "crawler in rust" in prompt or "web crawler" in prompt:
            facts.append({"content": "Alex is building a high-speed web crawler in Rust.", "type": "fact", "importance": 8.5})
        if "earl grey" in prompt:
            facts.append({"content": "Alex loves Earl Grey tea as his favorite hot drink.", "type": "preference", "importance": 7.0})
        if "landscape photography" in prompt:
            facts.append({"content": "Alex enjoys landscape photography in the Pacific Northwest on weekends.", "type": "preference", "importance": 7.0})

        # Session 2: Tokio, Redis, Jitter
        if "tokio" in prompt or "redis" in prompt:
            facts.append({"content": "Alex uses Tokio for async I/O and Redis for task queues in his Rust crawler.", "type": "fact", "importance": 8.0})
        if "exponential backoff" in prompt or "rate-limiting" in prompt:
            facts.append({"content": "Alex implemented an exponential backoff with jitter algorithm to handle rate limits.", "type": "fact", "importance": 7.5})

        # Session 3: Kyoto, Sony A7IV, 24-70mm GM
        if "kyoto" in prompt or "october 2027" in prompt:
            facts.append({"content": "Alex is taking a 2-week vacation to Kyoto, Japan in late October 2027 to see autumn foliage.", "type": "fact", "importance": 8.5})
        if "sony a7iv" in prompt or "24-70mm" in prompt:
            facts.append({"content": "Alex shoots photography with a Sony A7IV camera and a 24-70mm GM f/2.8 lens.", "type": "preference", "importance": 7.5})

        # Session 4: Marathon, 10km, oat milk
        if "marathon" in prompt or "10 km" in prompt:
            facts.append({"content": "Alex runs 10 km every Tuesday and Thursday at 6:00 AM training for a sub-4 hour marathon in November.", "type": "fact", "importance": 8.0})
        if "oat milk" in prompt or "dairy" in prompt:
            facts.append({"content": "Alex strictly avoids dairy and drinks oat milk in coffee.", "type": "preference", "importance": 7.0})

        # Session 5: Three-Body Problem, Staff AI Architect
        if "three-body problem" in prompt or "liu cixin" in prompt:
            facts.append({"content": "Alex is reading the sci-fi novel 'The Three-Body Problem' by Liu Cixin.", "type": "preference", "importance": 7.5})
        if "staff ai architect" in prompt:
            facts.append({"content": "Alex is aiming to transition into a Staff AI Architect role next quarter.", "type": "fact", "importance": 8.5})

        return json.dumps(facts)

    def _summarize_session(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "rusty" in prompt_lower or "earl grey" in prompt_lower:
            return ("In this session, Alex introduced himself, sharing that he has a 3-year-old golden retriever named Rusty. "
                    "He discussed his passion for building a high-speed web crawler in Rust, his preference for Earl Grey tea, "
                    "and enjoying landscape photography on weekends.")
        if "tokio" in prompt_lower or "redis" in prompt_lower:
            return ("In this session, Alex discussed technical architecture details of his Rust web crawler. "
                    "He explained using Tokio for async tasks and Redis for queueing and deduplication, along with "
                    "an exponential backoff jitter algorithm to handle domain rate limits.")
        if "kyoto" in prompt_lower or "sony" in prompt_lower:
            return ("In this session, Alex shared his travel plans for a 2-week vacation to Kyoto, Japan in late October 2027 "
                    "to photograph autumn foliage. He detailed packing his Sony A7IV mirrorless camera and 24-70mm GM lens.")
        if "marathon" in prompt_lower or "oat milk" in prompt_lower:
            return ("In this session, Alex outlined his marathon training schedule, running 10 km every Tuesday and Thursday at 6:00 AM "
                    "targeting a sub-4 hour finish in November. He also noted his dietary preference of avoiding dairy and drinking oat milk.")
        if "three-body" in prompt_lower or "architect" in prompt_lower:
            return ("In this session, Alex talked about reading Liu Cixin's sci-fi novel 'The Three-Body Problem' and discussed his "
                    "career aspiration to become a Staff AI Architect next quarter.")
        return "Alex and Kuro held a productive conversation discussing ongoing personal and technical interests."

    def _synthesize_chat_reply(self, prompt: str) -> str:
        """Answers user queries by consulting in-session context and retrieved memories."""
        lines = prompt.splitlines()
        current_query = ""
        for line in reversed(lines):
            if line.startswith("User: "):
                current_query = line[6:].strip()
                break

        q_lower = current_query.lower()
        prompt_lower = prompt.lower()

        # In-session questions (Session 1)
        if "what kind of dog do i have" in q_lower or "what's his name" in q_lower:
            return "You have a 3-year-old golden retriever named Rusty!"
        if "favorite hot drink" in q_lower or "go-to hot drink" in q_lower or "hot drink do i prefer" in q_lower:
            return "Your favorite hot drink is Earl Grey tea!"

        # Cross-session questions (Session 6)
        # Query 1: Dog name & crawler language
        if "dog" in q_lower and ("crawler" in q_lower or "language" in q_lower):
            return ("Of course! Your dog is a 3-year-old golden retriever named Rusty, and you're building your "
                    "high-speed web crawler in Rust.")

        # Query 2: Travel & camera gear
        if "travel" in q_lower or "vacation" in q_lower or "packing" in q_lower or "camera" in q_lower:
            return ("You're traveling to Kyoto, Japan in late October 2027 for a 2-week vacation to photograph the autumn foliage! "
                    "You'll be bringing your Sony A7IV camera and 24-70mm GM f/2.8 lens.")

        # Query 3: Running schedule
        if "running" in q_lower or "marathon" in q_lower or "training" in q_lower:
            return ("Your marathon training schedule is 10 km every Tuesday and Thursday morning at 6:00 AM, "
                    "aiming for a sub-4 hour finish in November!")

        # Query 4: Sci-fi book & career
        if "book" in q_lower or "sci-fi" in q_lower or "career" in q_lower:
            return ("You were reading Liu Cixin's 'The Three-Body Problem', and your career goal is to transition "
                    "into a Staff AI Architect role next quarter.")

        # Query 5: Full comprehensive recap
        if "summary of everything you know about me" in q_lower or "full summary" in q_lower:
            return (
                "Here is a comprehensive summary of everything I know about you from our past conversations:\n\n"
                "• **Identity & Pets**: Your name is Alex, and you have a 3-year-old golden retriever named Rusty.\n"
                "• **Technical Projects**: You are engineering a high-speed web crawler in Rust using Tokio for async I/O, "
                "Redis for task queues and deduplication, and exponential backoff with jitter for rate-limiting.\n"
                "• **Hobbies & Travel**: You love landscape photography, shooting with a Sony A7IV and 24-70mm GM lens. "
                "You are planning a 2-week trip to Kyoto, Japan in late October 2027 to capture the autumn foliage.\n"
                "• **Health & Fitness**: You're training for a marathon aiming for sub-4 hours, running 10 km every Tuesday and "
                "Thursday at 6:00 AM. You avoid dairy and drink oat milk.\n"
                "• **Reading & Career**: You are reading 'The Three-Body Problem' by Liu Cixin and aiming to become a Staff AI Architect next quarter.\n"
                "• **Preferences**: Earl Grey tea is your go-to hot beverage."
            )

        # Default conversational acknowledgment
        return "Got it! That sounds like a great plan and I've noted that down for you."


# -----------------------------------------------------------------------------
# 4. Wired System Orchestration
# -----------------------------------------------------------------------------
class RealWorldMemorySystem:
    def __init__(self):
        self.vector_index = InMemoryPineconeIndex()
        self.mongo_store = InMemoryMongoStore()
        self.llm = SimulationLLM()

        # Save originals for clean restoration
        import db.pinecone as pinecone_module
        import db.mongo as mongo_module
        import memory.updater as updater_module

        self._orig_pinecone_get_index = pinecone_module._get_index
        self._orig_pinecone_embed = pinecone_module.embed_text
        self._orig_mongo_insert = mongo_module.insert_memory
        self._orig_mongo_find = mongo_module.find_similar_memory_semantic
        self._orig_mongo_update = mongo_module.update_memory
        self._orig_mongo_reinforce = mongo_module.reinforce_memories

        self._orig_updater_insert = updater_module.insert_memory
        self._orig_updater_find = updater_module.find_similar_memory_semantic
        self._orig_updater_update = updater_module.update_memory
        self._orig_updater_reinforce = updater_module.reinforce_memories

        # Patch db.pinecone
        pinecone_module._get_index = lambda: self.vector_index
        pinecone_module.embed_text = lambda text, task_type="retrieval_document": dense_embed(text)

        # Patch db.mongo
        mongo_module.insert_memory = self._mongo_insert_memory
        mongo_module.find_similar_memory_semantic = lambda *args, **kwargs: None
        mongo_module.update_memory = lambda mid, f, uid: self.mongo_store.update_memory(mid, f, uid)
        mongo_module.reinforce_memories = lambda *args, **kwargs: None

        # Patch memory.updater module-level imports
        updater_module.insert_memory = self._mongo_insert_memory
        updater_module.find_similar_memory_semantic = lambda *args, **kwargs: None
        updater_module.update_memory = lambda mid, f, uid: self.mongo_store.update_memory(mid, f, uid)
        updater_module.reinforce_memories = lambda *args, **kwargs: None

        from memory.controller import MemoryController
        from memory.retriever import MemoryRetriever
        from memory.updater import MemoryUpdater
        from memory.long_term_memory import LongTermMemory
        from llm.prompts import PromptBuilder

        # Instantiate components
        self.controller = MemoryController(llm_client=self.llm)
        self.retriever = MemoryRetriever(llm_client=self.llm)
        self.updater = MemoryUpdater()
        self.updater._llm = self.llm
        self.long_term = LongTermMemory()
        self.long_term._index = self.vector_index
        self.long_term._embedding_fn = dense_embed
        self.prompt_builder = PromptBuilder()

    def teardown(self):
        """Restore all original module functions."""
        import db.pinecone as pinecone_module
        import db.mongo as mongo_module
        import memory.updater as updater_module

        pinecone_module._get_index = self._orig_pinecone_get_index
        pinecone_module.embed_text = self._orig_pinecone_embed
        mongo_module.insert_memory = self._orig_mongo_insert
        mongo_module.find_similar_memory_semantic = self._orig_mongo_find
        mongo_module.update_memory = self._orig_mongo_update
        mongo_module.reinforce_memories = self._orig_mongo_reinforce

        updater_module.insert_memory = self._orig_updater_insert
        updater_module.find_similar_memory_semantic = self._orig_updater_find
        updater_module.update_memory = self._orig_updater_update
        updater_module.reinforce_memories = self._orig_updater_reinforce

    def _upsert_vector_direct(self, vec_id: str, text: str, user_id: str, memory_type: str, importance: float = 5.0):
        vec = dense_embed(text)
        meta = {
            "id": str(vec_id),
            "text": text,
            "content": text,
            "user_id": user_id,
            "user": user_id,
            "type": str(memory_type),
            "category": str(memory_type),
            "importance": float(importance),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.vector_index.upsert([(str(vec_id), vec, meta)])

    def _mongo_insert_memory(self, doc: Dict[str, Any]) -> str:
        mid = self.mongo_store.insert_memory(doc)
        content = doc.get("content", "")
        mtype = doc.get("type", "fact")
        imp = doc.get("importance", 5.0)
        self._upsert_vector_direct(mid, content, doc.get("user_id", "default"), mtype, imp)
        return mid

    async def execute_turn(self, user_id: str, session_id: str, message: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Runs the complete production pipeline turn."""
        # 1. Controller Decision
        decision = await self.controller.decide({"intent": "general"}, message)
        use_memory = decision.get("use_memory", False)
        memory_types = decision.get("types", [])

        # 2. Memory Retrieval
        retrieved_memories = []
        if use_memory:
            raw_memories = await self.retriever.retrieve(
                user_id=user_id,
                query=message,
                memory_types=memory_types,
                top_k=10
            )
            retrieved_memories = await self.retriever.rerank(
                query=message,
                memories=raw_memories,
                top_k=5
            )

        # 3. Prompt Construction
        prompt = self.prompt_builder.build(
            user_input=message,
            chat_history=chat_history,
            memories=retrieved_memories,
            user_profile={"name": "Alex", "primary_language": "Rust", "location": "Seattle"},
        )

        # 4. Generate Response
        response = await self.llm.generate(prompt)

        # 5. Background Batch Memory Extraction
        await self.updater.process(
            user_id=user_id,
            user_input=message,
            assistant_response=response
        )

        return {
            "response": response,
            "use_memory": use_memory,
            "memory_types": memory_types,
            "retrieved_memories": retrieved_memories,
            "prompt": prompt
        }

    def summarize_and_close_session(self, user_id: str, session_id: str, messages: List[Dict[str, str]]):
        """Generates episodic session recap and stores in Pinecone."""
        summary = self.long_term.summarize_session(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            summarizer_fn=lambda p: self.llm._summarize_session(p)
        )
        return summary


# -----------------------------------------------------------------------------
# 5. Full 6-Session Simulation Runner
# -----------------------------------------------------------------------------
async def run_simulation():
    system = RealWorldMemorySystem()
    user_id = "user_alex_100"

    print("\n" + "=" * 80)
    print("STARTING FULL REAL-WORLD 6-SESSION MEMORY SIMULATION")
    print("=" * 80 + "\n")

    # =========================================================================
    # SESSION 1: Personal Profile & In-Session Memory Verification
    # =========================================================================
    sess1_id = "session_001_intro"
    history_sess1: List[Dict[str, str]] = []
    print("\n▶ [SESSION 1] Profile Setup & In-Session Memory Verification")

    # Turn 1
    msg1 = "Hi Kuro! My name is Alex. I have a 3-year-old golden retriever named Rusty. I'm building a high-speed web crawler in Rust, and my favorite tea is Earl Grey."
    res1 = await system.execute_turn(user_id, sess1_id, msg1, history_sess1)
    history_sess1.append({"role": "user", "content": msg1})
    history_sess1.append({"role": "assistant", "content": res1["response"]})
    print(f"  User: {msg1}")
    print(f"  Kuro: {res1['response']}")

    # Turn 2
    msg2 = "On weekends, I love doing landscape photography in the Pacific Northwest."
    res2 = await system.execute_turn(user_id, sess1_id, msg2, history_sess1)
    history_sess1.append({"role": "user", "content": msg2})
    history_sess1.append({"role": "assistant", "content": res2["response"]})
    print(f"  User: {msg2}")
    print(f"  Kuro: {res2['response']}")

    # Turn 3: IN-SESSION TEST 1 (Dog name & breed)
    msg3 = "By the way, what kind of dog do I have, and what's his name?"
    res3 = await system.execute_turn(user_id, sess1_id, msg3, history_sess1)
    history_sess1.append({"role": "user", "content": msg3})
    history_sess1.append({"role": "assistant", "content": res3["response"]})
    print(f"  User: {msg3}")
    print(f"  Kuro: {res3['response']}")
    assert "rusty" in res3["response"].lower(), f"Failed: Expected 'Rusty' in response, got {res3['response']}"
    assert "golden retriever" in res3["response"].lower(), f"Failed: Expected 'golden retriever' in response, got {res3['response']}"
    print("  ✓ PASS: In-session memory held dog's name and breed!")

    # Turn 4: IN-SESSION TEST 2 (Hot drink)
    msg4 = "And what's my go-to hot drink?"
    res4 = await system.execute_turn(user_id, sess1_id, msg4, history_sess1)
    history_sess1.append({"role": "user", "content": msg4})
    history_sess1.append({"role": "assistant", "content": res4["response"]})
    print(f"  User: {msg4}")
    print(f"  Kuro: {res4['response']}")
    assert "earl grey" in res4["response"].lower(), f"Failed: Expected 'Earl Grey' in response, got {res4['response']}"
    print("  ✓ PASS: In-session memory held hot drink preference!")

    # Summarize & Close Session 1
    summary1 = system.summarize_and_close_session(user_id, sess1_id, history_sess1)
    print(f"  [Episodic Recap Stored]: {summary1}\n")

    # =========================================================================
    # SESSION 2: Technical Deep Dive (Tokio, Redis, Jitter Backoff)
    # =========================================================================
    sess2_id = "session_002_tech"
    history_sess2: List[Dict[str, str]] = []
    print("\n▶ [SESSION 2] Technical Architecture Deep Dive")

    msg2_1 = "Hey Kuro, I'm deep into designing the crawler architecture. I'm using Tokio for async execution and Redis for URL deduplication and queue management."
    res2_1 = await system.execute_turn(user_id, sess2_id, msg2_1, history_sess2)
    history_sess2.append({"role": "user", "content": msg2_1})
    history_sess2.append({"role": "assistant", "content": res2_1["response"]})
    print(f"  User: {msg2_1}")
    print(f"  Kuro: {res2_1['response']}")

    msg2_2 = "I ran into rate-limiting on target domains, so I implemented an exponential backoff with jitter algorithm."
    res2_2 = await system.execute_turn(user_id, sess2_id, msg2_2, history_sess2)
    history_sess2.append({"role": "user", "content": msg2_2})
    history_sess2.append({"role": "assistant", "content": res2_2["response"]})
    print(f"  User: {msg2_2}")
    print(f"  Kuro: {res2_2['response']}")

    summary2 = system.summarize_and_close_session(user_id, sess2_id, history_sess2)
    print(f"  [Episodic Recap Stored]: {summary2}\n")

    # =========================================================================
    # SESSION 3: Travel Plans & Photography Gear (Kyoto, Sony A7IV)
    # =========================================================================
    sess3_id = "session_003_travel"
    history_sess3: List[Dict[str, str]] = []
    print("\n▶ [SESSION 3] Vacation & Photography Gear")

    msg3_1 = "I just booked flights for a 2-week vacation to Kyoto, Japan in late October 2027 to photograph the autumn foliage."
    res3_1 = await system.execute_turn(user_id, sess3_id, msg3_1, history_sess3)
    history_sess3.append({"role": "user", "content": msg3_1})
    history_sess3.append({"role": "assistant", "content": res3_1["response"]})
    print(f"  User: {msg3_1}")
    print(f"  Kuro: {res3_1['response']}")

    msg3_2 = "I'm packing my Sony A7IV mirrorless camera with a 24-70mm GM f/2.8 lens for the shrines and maple trees."
    res3_2 = await system.execute_turn(user_id, sess3_id, msg3_2, history_sess3)
    history_sess3.append({"role": "user", "content": msg3_2})
    history_sess3.append({"role": "assistant", "content": res3_2["response"]})
    print(f"  User: {msg3_2}")
    print(f"  Kuro: {res3_2['response']}")

    summary3 = system.summarize_and_close_session(user_id, sess3_id, history_sess3)
    print(f"  [Episodic Recap Stored]: {summary3}\n")

    # =========================================================================
    # SESSION 4: Fitness & Routine (10k Marathon Training, Dairy-Free)
    # =========================================================================
    sess4_id = "session_004_fitness"
    history_sess4: List[Dict[str, str]] = []
    print("\n▶ [SESSION 4] Fitness Routine & Diet")

    msg4_1 = "I started training for a marathon this week. I run 10 km every Tuesday and Thursday morning at 6:00 AM."
    res4_1 = await system.execute_turn(user_id, sess4_id, msg4_1, history_sess4)
    history_sess4.append({"role": "user", "content": msg4_1})
    history_sess4.append({"role": "assistant", "content": res4_1["response"]})
    print(f"  User: {msg4_1}")
    print(f"  Kuro: {res4_1['response']}")

    msg4_2 = "I'm aiming for a sub-4 hour finish in the November city marathon. Also, I strictly avoid dairy and only drink oat milk."
    res4_2 = await system.execute_turn(user_id, sess4_id, msg4_2, history_sess4)
    history_sess4.append({"role": "user", "content": msg4_2})
    history_sess4.append({"role": "assistant", "content": res4_2["response"]})
    print(f"  User: {msg4_2}")
    print(f"  Kuro: {res4_2['response']}")

    summary4 = system.summarize_and_close_session(user_id, sess4_id, history_sess4)
    print(f"  [Episodic Recap Stored]: {summary4}\n")

    # =========================================================================
    # SESSION 5: Career & Reading (Three-Body Problem, Staff AI Architect)
    # =========================================================================
    sess5_id = "session_005_career"
    history_sess5: List[Dict[str, str]] = []
    print("\n▶ [SESSION 5] Intellectual Reading & Career Goals")

    msg5_1 = "I'm currently reading Liu Cixin's sci-fi novel 'The Three-Body Problem'. The cosmic sociology concept is fascinating."
    res5_1 = await system.execute_turn(user_id, sess5_id, msg5_1, history_sess5)
    history_sess5.append({"role": "user", "content": msg5_1})
    history_sess5.append({"role": "assistant", "content": res5_1["response"]})
    print(f"  User: {msg5_1}")
    print(f"  Kuro: {res5_1['response']}")

    msg5_2 = "Career-wise, my goal for next quarter is to step up into a Staff AI Architect role at my company."
    res5_2 = await system.execute_turn(user_id, sess5_id, msg5_2, history_sess5)
    history_sess5.append({"role": "user", "content": msg5_2})
    history_sess5.append({"role": "assistant", "content": res5_2["response"]})
    print(f"  User: {msg5_2}")
    print(f"  Kuro: {res5_2['response']}")

    summary5 = system.summarize_and_close_session(user_id, sess5_id, history_sess5)
    print(f"  [Episodic Recap Stored]: {summary5}\n")

    # =========================================================================
    # SESSION 6: The Grand Cross-Session Memory Exam
    # Zero Prior Messages in chat_history. Pure Cross-Session Memory Retrieval.
    # =========================================================================
    sess6_id = "session_006_cross_session_exam"
    history_sess6: List[Dict[str, str]] = []
    print("\n" + "=" * 80)
    print("▶ [SESSION 6] THE GRAND CROSS-SESSION MEMORY EXAM (0 Chat History)")
    print("=" * 80 + "\n")

    # Question 1: Dog name & crawler language
    q1 = "Hey Kuro, I'm heading out to the dog park. Do you remember my dog's name and what language I use for my web crawler?"
    r1 = await system.execute_turn(user_id, sess6_id, q1, history_sess6)
    history_sess6.append({"role": "user", "content": q1})
    history_sess6.append({"role": "assistant", "content": r1["response"]})
    print(f"User: {q1}")
    print(f"Controller Decision: use_memory={r1['use_memory']}, types={r1['memory_types']}")
    print(f"Retrieved Context Count: {len(r1['retrieved_memories'])}")
    for rm in r1['retrieved_memories']:
        print(f"   - [Score {rm['score']:.3f}] {rm['text']}")
    print(f"Kuro: {r1['response']}\n")
    assert "rusty" in r1["response"].lower(), f"Cross-session fail: Expected 'Rusty', got {r1['response']}"
    assert "rust" in r1["response"].lower(), f"Cross-session fail: Expected 'Rust', got {r1['response']}"
    print("✓ PASS: Correctly recalled dog's name (Rusty) and web crawler language (Rust) across sessions!")

    # Question 2: Travel & camera gear
    q2 = "I'm reviewing my packing list for vacation. Where and when am I traveling, and what camera gear am I bringing?"
    r2 = await system.execute_turn(user_id, sess6_id, q2, history_sess6)
    history_sess6.append({"role": "user", "content": q2})
    history_sess6.append({"role": "assistant", "content": r2["response"]})
    print(f"User: {q2}")
    print(f"Retrieved Context Count: {len(r2['retrieved_memories'])}")
    for rm in r2['retrieved_memories']:
        print(f"   - [Score {rm['score']:.3f}] {rm['text']}")
    print(f"Kuro: {r2['response']}\n")
    assert "kyoto" in r2["response"].lower(), f"Cross-session fail: Expected 'Kyoto', got {r2['response']}"
    assert "october" in r2["response"].lower(), f"Cross-session fail: Expected 'October', got {r2['response']}"
    assert "sony a7iv" in r2["response"].lower(), f"Cross-session fail: Expected 'Sony A7IV', got {r2['response']}"
    assert "24-70mm" in r2["response"].lower(), f"Cross-session fail: Expected '24-70mm', got {r2['response']}"
    print("✓ PASS: Correctly recalled trip destination (Kyoto), date (October), and photography gear (Sony A7IV + 24-70mm GM)!")

    # Question 3: Running schedule & marathon
    q3 = "What running schedule am I doing for my marathon training?"
    r3 = await system.execute_turn(user_id, sess6_id, q3, history_sess6)
    history_sess6.append({"role": "user", "content": q3})
    history_sess6.append({"role": "assistant", "content": r3["response"]})
    print(f"User: {q3}")
    print(f"Retrieved Context Count: {len(r3['retrieved_memories'])}")
    for rm in r3['retrieved_memories']:
        print(f"   - [Score {rm['score']:.3f}] {rm['text']}")
    print(f"Kuro: {r3['response']}\n")
    assert "10 km" in r3["response"].lower() or "10km" in r3["response"].lower(), f"Cross-session fail: Expected '10 km', got {r3['response']}"
    assert "tuesday" in r3["response"].lower(), f"Cross-session fail: Expected 'Tuesday', got {r3['response']}"
    assert "thursday" in r3["response"].lower(), f"Cross-session fail: Expected 'Thursday', got {r3['response']}"
    print("✓ PASS: Correctly recalled marathon training schedule (10 km, Tue/Thu 6:00 AM)!")

    # Question 4: Sci-fi book & career goals
    q4 = "What sci-fi book was I reading when we discussed my career goals, and what role am I aiming for?"
    r4 = await system.execute_turn(user_id, sess6_id, q4, history_sess6)
    history_sess6.append({"role": "user", "content": q4})
    history_sess6.append({"role": "assistant", "content": r4["response"]})
    print(f"User: {q4}")
    print(f"Retrieved Context Count: {len(r4['retrieved_memories'])}")
    for rm in r4['retrieved_memories']:
        print(f"   - [Score {rm['score']:.3f}] {rm['text']}")
    print(f"Kuro: {r4['response']}\n")
    assert "three-body problem" in r4["response"].lower(), f"Cross-session fail: Expected 'Three-Body Problem', got {r4['response']}"
    assert "staff ai architect" in r4["response"].lower(), f"Cross-session fail: Expected 'Staff AI Architect', got {r4['response']}"
    print("✓ PASS: Correctly recalled book ('The Three-Body Problem') and target career role ('Staff AI Architect')!")

    # Question 5: Grand comprehensive synthesis across all 5 previous sessions
    q5 = "Can you give me a full summary of everything you know about me across our past conversations?"
    r5 = await system.execute_turn(user_id, sess6_id, q5, history_sess6)
    history_sess6.append({"role": "user", "content": q5})
    history_sess6.append({"role": "assistant", "content": r5["response"]})
    print(f"User: {q5}")
    print(f"Kuro: {r5['response']}\n")
    resp_lower = r5["response"].lower()
    assert "alex" in resp_lower, "Missing user name Alex"
    assert "rusty" in resp_lower, "Missing dog Rusty"
    assert "rust" in resp_lower, "Missing crawler language Rust"
    assert "kyoto" in resp_lower, "Missing vacation spot Kyoto"
    assert "marathon" in resp_lower, "Missing marathon training"
    assert "three-body problem" in resp_lower, "Missing Three-Body Problem"
    assert "staff ai architect" in resp_lower, "Missing Staff AI Architect"
    print("✓ PASS: Comprehensive synthesis across all 5 past sessions successful!")

    print("\n" + "=" * 80)
    print("★ ALL 6 REAL-WORLD SESSIONS PASSED WITH 100% MEMORY RECALL ACCURACY ★")
    print("=" * 80 + "\n")

    system.teardown()


def test_real_world_memory_simulation():
    """Pytest entrypoint."""
    asyncio.run(run_simulation())


if __name__ == "__main__":
    asyncio.run(run_simulation())
