"""
Ultra-lightweight memory manager for Render's 512MB memory limit
Uses only Google Gemini embeddings and basic Python operations
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import math

# Google Gemini imports
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class UltraLightweightMemoryManager:
    """Memory manager optimized for minimal memory usage"""
    
    def __init__(self):
        # Initialize Google Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.embedding_model = "models/text-embedding-004"
        
        # Initialize Pinecone (lightweight connection)
        from pinecone import Pinecone
        pc_api_key = os.getenv("PINECONE_API_KEY")
        if not pc_api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
        
        self.pc = Pinecone(api_key=pc_api_key)
        index_name = os.getenv("PINECONE_INDEX", "ai-memory")
        self.index = self.pc.Index(index_name)
        
        logger.info("Ultra-lightweight memory manager initialized")
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity without numpy"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Google Gemini"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a default embedding vector of appropriate size
            return [0.0] * 768  # Standard embedding size
    
    def store_memory(self, text: str, metadata: Dict[str, Any]) -> str:
        """Store a memory with minimal processing"""
        try:
            # Generate embedding
            embedding = self.get_embedding(text)
            
            # Create memory ID
            import uuid
            memory_id = str(uuid.uuid4())
            
            # Enhanced metadata with defaults
            enhanced_metadata = {
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "importance": metadata.get("importance", 0.5),
                "category": metadata.get("category", "general"),
                "user": metadata.get("user", "unknown"),
                **metadata
            }
            
            # Store in Pinecone
            self.index.upsert([(memory_id, embedding, enhanced_metadata)])
            
            logger.info(f"Memory stored: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise
    
    def get_relevant_memories(self, query: str, user_filter: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories"""
        try:
            # Generate query embedding
            query_embedding = self.get_embedding(query)
            
            # Build filter
            filter_dict = {}
            if user_filter:
                filter_dict["user"] = user_filter
            
            # Query Pinecone
            query_kwargs = {
                "vector": query_embedding,
                "top_k": top_k,
                "include_metadata": True
            }
            
            if filter_dict:
                query_kwargs["filter"] = filter_dict
            
            results = self.index.query(**query_kwargs)
            
            # Format results
            memories = []
            for match in results.matches:
                memory = {
                    "text": match.metadata.get("text", ""),
                    "score": float(match.score),
                    "importance": match.metadata.get("importance", 0.5),
                    "category": match.metadata.get("category", "general"),
                    "timestamp": match.metadata.get("timestamp", "")
                }
                memories.append(memory)
            
            logger.info(f"Retrieved {len(memories)} memories")
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get basic user context"""
        try:
            # Get recent memories
            memories = self.get_relevant_memories("user preferences goals name", user_filter=user_id, top_k=10)
            
            context = {
                "recent_memories": len(memories),
                "topics": list(set(m.get("category", "general") for m in memories)),
                "last_interaction": max([m.get("timestamp", "") for m in memories]) if memories else ""
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}
    
    def cleanup_old_memories(self, user_id: str, days_threshold: int = 30):
        """Basic cleanup - just log for now"""
        logger.info(f"Cleanup requested for user {user_id} (threshold: {days_threshold} days)")
        # Simplified - just return success for now
        return True

# Global instance
ultra_lightweight_memory_manager = UltraLightweightMemoryManager()

def store_memory(text: str, metadata: Dict[str, Any]) -> str:
    """Store memory function"""
    return ultra_lightweight_memory_manager.store_memory(text, metadata)

def get_relevant_memories_detailed(query: str, user_filter: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """Get relevant memories function"""
    return ultra_lightweight_memory_manager.get_relevant_memories(query, user_filter, top_k)
