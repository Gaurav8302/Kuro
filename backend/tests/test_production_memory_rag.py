import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from memory.controller import MemoryController, RECALL_PATTERNS
from memory.retriever import MemoryRetriever
from memory.updater import MemoryUpdater
from memory.provenance import MemoryRecord, MemoryType, MemorySource
from llm.prompts import PromptBuilder


# ---------------------------------------------------------------------------
# Test 1: In-Session Memory & PromptBuilder Context Preservation
# ---------------------------------------------------------------------------
def test_prompt_builder_expands_beyond_five_turns():
    builder = PromptBuilder()
    
    # Create 30 messages (15 exchanges)
    chat_history = []
    for i in range(15):
        chat_history.append({"role": "user", "content": f"User question {i+1}"})
        chat_history.append({"role": "assistant", "content": f"Assistant answer {i+1}"})
    
    prompt = builder.build(
        user_input="Current test query",
        chat_history=chat_history,
        memories=[{"text": "User loves Python", "metadata": {"category": "preference"}}],
        user_profile={"name": "Gaurav"},
    )
    
    # Verify user profile is present
    assert "Name: Gaurav" in prompt
    # Verify long-term memory is present
    assert "User loves Python" in prompt
    # Verify recent turns (e.g. Turn 14, 15) are present in prompt
    assert "User question 15" in prompt
    assert "Assistant answer 15" in prompt
    assert "User question 6" in prompt  # Was previously dropped by [-10:]!


def test_prompt_builder_compacts_earlier_context():
    builder = PromptBuilder()
    
    # Create 35 messages
    chat_history = []
    for i in range(35):
        chat_history.append({"role": "user", "content": f"Discussion topic number {i+1} with detailed explanation"})
        chat_history.append({"role": "assistant", "content": f"Acknowledged topic {i+1}"})
    
    prompt = builder.build(
        user_input="Current query",
        chat_history=chat_history,
        memories=[],
        session_summary="Earlier the user and assistant planned the architecture.",
    )
    
    assert "Earlier Discussion in this Session:" in prompt
    assert "planned the architecture" in prompt


# ---------------------------------------------------------------------------
# Test 2: MemoryController Fast Pattern Matching & Zero Latency Trigger
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_memory_controller_recall_patterns():
    controller = MemoryController()
    
    # Test recall phrases
    test_queries = [
        "Do you remember what my favorite programming language was?",
        "What did we discuss last time?",
        "Recall what I said earlier about my project",
        "Who am I?",
        "What do you know about me?",
        "Continue where we left off",
    ]
    
    for q in test_queries:
        decision = await controller.decide(intent_data={"intent": "general"}, user_input=q)
        assert decision["use_memory"] is True, f"Failed for query: {q}"
        assert "fact" in decision["types"]
        assert "session_summary" in decision["types"]


@pytest.mark.anyio
async def test_memory_controller_skips_casual_chit_chat():
    controller = MemoryController()
    
    casual_queries = ["hi", "hello", "ok", "cool thanks"]
    for q in casual_queries:
        decision = await controller.decide(intent_data={"intent": "casual"}, user_input=q)
        assert decision["use_memory"] is False, f"Should skip for casual: {q}"


# ---------------------------------------------------------------------------
# Test 3: Pinecone Metadata Normalization & No 0-Match Bug
# ---------------------------------------------------------------------------
def test_pinecone_upsert_normalizes_metadata():
    with patch("db.pinecone._get_index") as mock_get_index, \
         patch("db.pinecone.embed_text", return_value=[0.1] * 768):
        mock_index = MagicMock()
        mock_get_index.return_value = mock_index
        
        from db.pinecone import upsert_vector
        
        # Test with MemoryType Enum
        upsert_vector("vec_1", "User prefers dark theme", "user_123", MemoryType.PREFERENCE, 8.5)
        
        args, kwargs = mock_index.upsert.call_args
        vectors = kwargs.get("vectors") or args[0]
        vec_id, vec, meta = vectors[0]
        
        assert vec_id == "vec_1"
        assert meta["user_id"] == "user_123"
        assert meta["user"] == "user_123"
        assert meta["type"] == "preference"
        assert meta["category"] == "preference"
        assert meta["content"] == "User prefers dark theme"
        assert meta["text"] == "User prefers dark theme"
        assert meta["importance"] == 8.5


def test_pinecone_query_handles_plural_and_singular_types():
    with patch("db.pinecone._get_index") as mock_get_index, \
         patch("db.pinecone.embed_text", return_value=[0.1] * 768):
        mock_index = MagicMock()
        mock_get_index.return_value = mock_index
        mock_match = MagicMock()
        mock_match.metadata = {"content": "User works at Google", "type": "fact", "importance": 7.0}
        mock_match.score = 0.88
        mock_index.query.return_value.matches = [mock_match]
        
        from db.pinecone import query_vectors
        
        results = query_vectors("query", "user_123", ["fact"], top_k=5)
        assert len(results) == 1
        assert results[0]["text"] == "User works at Google"
        assert results[0]["score"] == 0.88
        
        # Check filter dictionary passed to Pinecone
        _, kwargs = mock_index.query.call_args
        filter_dict = kwargs.get("filter")
        assert filter_dict["user_id"]["$eq"] == "user_123"
        # Should contain both singular and plural forms
        assert "fact" in filter_dict["type"]["$in"]
        assert "facts" in filter_dict["type"]["$in"]


# ---------------------------------------------------------------------------
# Test 4: MemoryRetriever Ranking & Threshold Safety
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_memory_retriever_preserves_valid_memories():
    with patch("memory.retriever.query_vectors") as mock_query:
        mock_query.return_value = [
            # High similarity, low importance (importance <= 3 was previously dropped by bug!)
            {"text": "User lives in Seattle", "score": 0.95, "metadata": {"importance": 2.0}},
            # Medium similarity, high importance
            {"text": "User has a dog named Spot", "score": 0.70, "metadata": {"importance": 9.0}},
        ]
        
        retriever = MemoryRetriever()
        memories = await retriever.retrieve("user_123", "where do I live", ["fact"], top_k=5)
        
        assert len(memories) == 2, "Valid memory with importance 2.0 must NOT be dropped!"
        # The high similarity memory should rank first (0.95 * 0.80 + 0.20 * 0.20 = 0.80) vs (0.70 * 0.80 + 0.90 * 0.20 = 0.74)
        assert memories[0]["text"] == "User lives in Seattle"


@pytest.mark.anyio
async def test_memory_retriever_fast_rerank():
    retriever = MemoryRetriever()
    memories = [
        {"text": "User loves pizza on weekends", "score": 0.65, "metadata": {"importance": 5.0}},
        {"text": "User favorite food is Italian pizza Margherita", "score": 0.75, "metadata": {"importance": 6.0}},
    ]
    
    reranked = await retriever.rerank("pizza Margherita", memories, top_k=2)
    assert len(reranked) == 2
    assert "Margherita" in reranked[0]["text"]


# ---------------------------------------------------------------------------
# Test 5: Streamlined Batch Memory Extraction
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_memory_updater_batch_extraction():
    updater = MemoryUpdater()
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = """[
        {"type": "preference", "content": "Prefers FastAPI for backend", "importance": 8.0},
        {"type": "fact", "content": "Lives in Bangalore", "importance": 7.0}
    ]"""
    updater._llm = mock_llm
    
    items = await updater.extract_memory_batch(
        "I really prefer using FastAPI for building python backends and I live in Bangalore",
        "FastAPI is a great choice!"
    )
    
    assert len(items) == 2
    assert items[0]["content"] == "Prefers FastAPI for backend"
    assert items[0]["type"] == "preference"
    assert items[0]["importance"] == 8.0


# ---------------------------------------------------------------------------
# Test 6: Document RAG Ingestion Pipeline
# ---------------------------------------------------------------------------
def test_rag_document_processor_chunk_and_store():
    with patch("db.pinecone._get_index") as mock_get_index, \
         patch("db.pinecone.embed_text", return_value=[0.05] * 768):
        mock_index = MagicMock()
        mock_get_index.return_value = mock_index
        
        from rag.pipeline import DocumentProcessor
        
        processor = DocumentProcessor()
        doc_content = b"This is a production specification document for Kuro AI memory system. It contains critical instructions and architecture."
        
        result = processor.ingest_document(
            file_content=doc_content,
            filename="spec.txt",
            user_id="user_test_99",
            mime_type="text/plain"
        )
        
        assert result["filename"] == "spec.txt"
        assert result["chunk_count"] >= 1
        assert mock_index.upsert.called, "Pinecone index.upsert must be called during document ingestion!"


# ---------------------------------------------------------------------------
# Test 7: FastAPI Endpoint Integration (Summarize, RAG Ingest, RAG Search)
# ---------------------------------------------------------------------------
def _make_test_token(sub: str, **extra_claims) -> str:
    import jwt
    from security.auth import get_test_private_key
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        "sub": sub,
        "iss": "https://test-clerk.example",
        "exp": now + 3600,
        "nbf": now - 60,
        "aud": "kuro-api",
        **extra_claims,
    }
    private_key = get_test_private_key()
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key-1"})


def test_api_session_summarize_endpoint():
    from fastapi.testclient import TestClient
    from chatbot import app
    from memory.chat_database import chat_db

    token = _make_test_token(sub="user_prod_1")
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"})

    mock_titles = MagicMock()
    with patch.object(chat_db, "session_belongs_to_user", return_value=True), \
         patch.object(chat_db, "session_titles", mock_titles), \
         patch("memory.chat_database.get_chat_by_session", return_value=[
             {"user": "What is our architecture plan?", "assistant": "We are building a 3-tier memory system."}
         ]), \
         patch("memory.long_term_memory.long_term_memory.summarize_session", return_value="Session planned a 3-tier memory system."):
        
        response = client.post("/session/summarize/sess_123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"] == "Session planned a 3-tier memory system."
        assert data["session_id"] == "sess_123"
        assert mock_titles.update_one.called


def test_api_document_ingest_and_search_endpoints():
    from fastapi.testclient import TestClient
    from chatbot import app

    token = _make_test_token(sub="user_prod_2")
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"})

    with patch("db.pinecone._get_index") as mock_get_index, \
         patch("db.pinecone.embed_text", return_value=[0.02] * 768), \
         patch("db.pinecone.query_vectors") as mock_query:
        
        mock_index = MagicMock()
        mock_get_index.return_value = mock_index
        mock_query.return_value = [
            {"text": "Chunk from architecture guide", "score": 0.89, "metadata": {"filename": "arch.md"}}
        ]

        # 1. Test Ingestion
        ingest_payload = {
            "filename": "architecture.md",
            "content": "# Kuro Architecture\nKuro AI features unified long-term memory and retrieval.",
            "mime_type": "text/markdown",
            "metadata": {"project": "kuro"}
        }
        res_ingest = client.post("/documents/ingest", json=ingest_payload)
        assert res_ingest.status_code == 200
        data_ingest = res_ingest.json()
        assert data_ingest["status"] == "success"
        assert data_ingest["filename"] == "architecture.md"
        assert data_ingest["chunk_count"] >= 1

        # 2. Test Search
        search_payload = {
            "query": "architecture guide",
            "top_k": 3
        }
        res_search = client.post("/documents/search", json=search_payload)
        assert res_search.status_code == 200
        data_search = res_search.json()
        assert len(data_search["results"]) == 1
        assert data_search["results"][0]["text"] == "Chunk from architecture guide"

