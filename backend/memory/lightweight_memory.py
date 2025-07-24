# Lightweight memory manager without heavy ML dependencies
# Uses Google Gemini for embeddings instead of local models

import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import numpy as np
from datetime import datetime, timedelta
import os
import google.generativeai as genai
from memory.pinecone_setup import get_pinecone_index

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightweightMemoryManager:
    def __init__(self):
        self.index = None
        self.model_initialized = False
        
    def _init_if_needed(self):
        """Lazy initialization to reduce startup memory"""
        if not self.model_initialized:
            try:
                # Configure Gemini for embeddings
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                self.index = get_pinecone_index()
                self.model_initialized = True
                logger.info("✅ Lightweight memory manager initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize memory manager: {e}")
                raise

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using Google's embedding API (lightweight)"""
        self._init_if_needed()
        
        try:
            embeddings = []
            for text in texts:
                # Use Gemini's embedding model (much lighter than sentence-transformers)
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            return embeddings
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            # Fallback: simple text-based similarity (no ML)
            return [[hash(text) % 1000 / 1000.0] * 384 for text in texts]

    def store_memory(self, user_id: str, text: str, context_type: str = "conversation") -> bool:
        """Store memory with lightweight embedding"""
        try:
            self._init_if_needed()
            
            # Generate embedding
            embeddings = self.get_embeddings([text])
            if not embeddings:
                return False
                
            # Store in Pinecone
            vector_id = f"{user_id}_{datetime.now().timestamp()}"
            metadata = {
                "user_id": user_id,
                "text": text,
                "context_type": context_type,
                "timestamp": datetime.now().isoformat()
            }
            
            self.index.upsert([{
                "id": vector_id,
                "values": embeddings[0],
                "metadata": metadata
            }])
            
            return True
        except Exception as e:
            logger.error(f"❌ Memory storage failed: {e}")
            return False

    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant memories"""
        try:
            self._init_if_needed()
            
            # Generate query embedding
            query_embeddings = self.get_embeddings([query])
            if not query_embeddings:
                return []
            
            # Search in Pinecone
            results = self.index.query(
                vector=query_embeddings[0],
                filter={"user_id": user_id},
                top_k=limit,
                include_metadata=True
            )
            
            memories = []
            for match in results.matches:
                memories.append({
                    "text": match.metadata.get("text", ""),
                    "score": float(match.score),
                    "timestamp": match.metadata.get("timestamp", ""),
                    "context_type": match.metadata.get("context_type", "conversation")
                })
            
            return memories
        except Exception as e:
            logger.error(f"❌ Memory retrieval failed: {e}")
            return []

# Global instance
lightweight_memory_manager = LightweightMemoryManager()

# Export functions for backward compatibility
def store_memory(user_id: str, text: str, context_type: str = "conversation") -> bool:
    return lightweight_memory_manager.store_memory(user_id, text, context_type)

def get_relevant_memories_detailed(user_id: str, query: str, limit: int = 5) -> List[Dict]:
    return lightweight_memory_manager.get_relevant_memories(user_id, query, limit)
