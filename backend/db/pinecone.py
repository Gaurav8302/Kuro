import os
import google.generativeai as genai
from pinecone import Pinecone

_pc = None
_index = None

def _get_index():
    global _pc, _index
    if _index is None:
        pc_api_key = os.getenv("PINECONE_API_KEY")
        if pc_api_key:
            _pc = Pinecone(api_key=pc_api_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", "my-chatbot-memory")
            _index = _pc.Index(index_name)
    return _index

def _embed_text(text):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        vec = result["embedding"]
        if len(vec) > 384:
            vec = vec[::2][:384]
        elif len(vec) < 384:
            vec.extend([0.0] * (384 - len(vec)))
        return vec
    except Exception as e:
        print(f"Error embedding text: {e}")
        return [0.0] * 384

def upsert_vector(vec_id, text, user_id, memory_type, importance):
    index = _get_index()
    if not index:
        return
    
    vec = _embed_text(text)
    metadata = {
        "content": text,
        "user_id": user_id,
        "type": memory_type,
        "importance": importance
    }
    
    try:
        index.upsert(vectors=[(vec_id, vec, metadata)])
    except Exception as e:
        print(f"Pinecone upsert error: {e}")

def query_vectors(query, user_id, memory_types, top_k):
    index = _get_index()
    if not index:
        return []
    
    vec = _embed_text(query)
    filter_dict = {"user_id": user_id}
    if memory_types:
        filter_dict["type"] = {"$in": memory_types}

    try:
        results = index.query(
            vector=vec,
            filter=filter_dict,
            top_k=top_k,
            include_metadata=True
        )
        return [match.metadata.get("content", "") for match in results.matches]
    except Exception as e:
        print(f"Pinecone query error: {e}")
        return []
