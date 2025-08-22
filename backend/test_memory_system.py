#!/usr/bin/env python3
"""
Test script to check Pinecone index configuration and embedding dimensions
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def test_embedding():
    """Test Google Gemini embedding"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        return
    
    genai.configure(api_key=api_key)
    
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content="test message",
            task_type="retrieval_document"
        )
        embedding = result['embedding']
        print(f"✅ Gemini embedding dimension: {len(embedding)}")
        
        # Test dimension reduction
        if len(embedding) > 384:
            reduced = embedding[::2][:384]
            print(f"✅ Reduced embedding dimension: {len(reduced)}")
        
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")

def test_pinecone():
    """Test Pinecone connection"""
    try:
        from pinecone import Pinecone
        
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME", "my-chatbot-memory")
        
        if not api_key:
            print("❌ PINECONE_API_KEY not found")
            return
        
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        
        # Get index stats
        stats = index.describe_index_stats()
        print(f"✅ Pinecone index '{index_name}' connected")
        print(f"   Dimension: {stats.get('dimension', 'unknown')}")
        print(f"   Total vectors: {stats.get('total_vector_count', 0)}")
        
    except Exception as e:
        print(f"❌ Pinecone test failed: {e}")

if __name__ == "__main__":
    print("🔍 Testing memory system components...")
    print("\n" + "="*50)
    print("Testing Google Gemini embeddings:")
    test_embedding()
    
    print("\n" + "="*50)
    print("Testing Pinecone connection:")
    test_pinecone()
    
    print("\n✅ Test complete!")
