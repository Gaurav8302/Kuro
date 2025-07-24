"""
Memory Management Module

This module handles the storage and retrieval of user memories using Pinecone
vector database. It provides semantic search capabilities for the AI chatbot
to maintain context and personalization across conversations.

Features:
- Vector embedding using sentence transformers
- Pinecone vector database integration
- User-isolated memory storage
- Semantic similarity search
- Memory metadata management
"""

import os
import logging
from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "my-chatbot-memory")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable is required")

class MemoryManager:
    """
    Enhanced memory management class for handling vector storage and retrieval
    
    This class provides methods to store and retrieve memories using
    Pinecone vector database with semantic search capabilities.
    Features cross-session memory continuity and importance scoring.
    """
    
    def __init__(self):
        """Initialize the memory manager with Pinecone and embedding model"""
        self._initialize_pinecone()
        self._initialize_embedding_model()
        self._memory_cache = {}  # Local cache for frequently accessed memories
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection and index"""
        try:
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=PINECONE_API_KEY)
            
            # Create index if it doesn't exist
            existing_indexes = self.pc.list_indexes().names()
            if PINECONE_INDEX_NAME not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
                self.pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=384,  # Dimension for all-MiniLM-L6-v2 model
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
                )
            
            # Connect to the index
            self.index = self.pc.Index(PINECONE_INDEX_NAME)
            logger.info(f"✅ Connected to Pinecone index: {PINECONE_INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone: {str(e)}")
            raise ConnectionError(f"Pinecone initialization failed: {str(e)}")
    
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model for embeddings"""
        try:
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
            raise RuntimeError(f"Embedding model initialization failed: {str(e)}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Convert text to vector embedding
        
        Args:
            text (str): Text to embed
            
        Returns:
            List[float]: Vector embedding
        """
        try:
            embedding = self.model.encode([text])[0].tolist()
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed text: {str(e)}")
            raise RuntimeError(f"Text embedding failed: {str(e)}")
    
    def store_memory(self, text: str, metadata: Dict[str, Any], importance: float = 1.0) -> str:
        """
        Store a memory in the vector database with enhanced metadata and importance scoring
        
        Args:
            text (str): Memory text content
            metadata (dict): Additional metadata for the memory
            importance (float): Memory importance score (0.0 to 1.0)
            
        Returns:
            str: Unique ID of the stored memory
            
        Raises:
            ValueError: If required metadata is missing
            RuntimeError: If storage fails
        """
        try:
            # Validate required metadata
            if "user" not in metadata:
                raise ValueError("Missing 'user' field in metadata. Cannot store memory without user ID.")
            
            # Enhanced metadata with automatic categorization
            enhanced_metadata = {
                **metadata,
                "timestamp": datetime.utcnow().isoformat(),
                "importance": max(0.0, min(1.0, importance)),  # Clamp between 0 and 1
                "memory_text": text,
                "word_count": len(text.split()),
                "session_context": metadata.get("session_id", "cross_session"),
                "memory_type": self._categorize_memory(text, metadata),
                "access_count": 0,
                "last_accessed": datetime.utcnow().isoformat()
            }
            
            # Generate embedding and unique ID
            embedding = self.embed_text(text)
            memory_id = str(uuid4())
            
            # Store in Pinecone with enhanced metadata
            self.index.upsert(vectors=[
                {
                    "id": memory_id,
                    "values": embedding,
                    "metadata": enhanced_metadata
                }
            ])
            
            # Update local cache for frequently accessed memories
            user_id = metadata["user"]
            if user_id not in self._memory_cache:
                self._memory_cache[user_id] = []
            
            # Keep only top 20 most important memories in cache per user
            self._memory_cache[user_id].append({
                "id": memory_id,
                "text": text,
                "importance": importance,
                "timestamp": enhanced_metadata["timestamp"]
            })
            
            # Sort by importance and keep top memories
            self._memory_cache[user_id].sort(key=lambda x: x["importance"], reverse=True)
            self._memory_cache[user_id] = self._memory_cache[user_id][:20]
            
            logger.info(f"✅ Memory stored successfully: {memory_id[:8]}... (importance: {importance})")
            return memory_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store memory: {str(e)}")
            raise RuntimeError(f"Memory storage failed: {str(e)}")
    
    def _categorize_memory(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Automatically categorize memory based on content and metadata
        
        Args:
            text (str): Memory text content
            metadata (dict): Memory metadata
            
        Returns:
            str: Memory category
        """
        text_lower = text.lower()
        
        # User profile information
        if any(keyword in text_lower for keyword in ["my name is", "i am", "call me", "i'm"]):
            return "user_profile"
        
        # Preferences and interests
        if any(keyword in text_lower for keyword in ["i like", "i love", "i prefer", "favorite", "interested in"]):
            return "preferences"
        
        # Important facts or key information
        if any(keyword in text_lower for keyword in ["remember", "important", "key", "note", "don't forget"]):
            return "key_information"
        
        # Goals and aspirations
        if any(keyword in text_lower for keyword in ["goal", "want to", "plan to", "hoping", "dream"]):
            return "goals"
        
        # Skills and capabilities
        if any(keyword in text_lower for keyword in ["good at", "skilled", "experienced", "know how"]):
            return "skills"
        
        # Conversational exchanges
        if metadata.get("type") == "chat_exchange":
            return "conversation"
        
        return "general"
                }
            ])
            
            logger.info(f"Memory stored successfully: {vector_id} for user {metadata['user']}")
            return vector_id
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to store memory: {str(e)}")
            raise RuntimeError(f"Memory storage failed: {str(e)}")
    
    def get_relevant_memories(
        self, 
        query: str, 
        user_filter: Optional[str] = None, 
        top_k: int = 5,
        score_threshold: float = 0.6
    ) -> List[str]:
        """
        Retrieve relevant memories based on a query
        
        Args:
            query (str): Query text for similarity search
            user_filter (str, optional): Filter memories by user ID
            top_k (int): Maximum number of memories to retrieve
            score_threshold (float): Minimum similarity score threshold
            
        Returns:
            List[str]: List of relevant memory texts
        """
        try:
            # Generate query embedding
            query_vector = self.embed_text(query)
            
            # Apply user filter if provided
            filter_dict = {"user": {"$eq": user_filter}} if user_filter else {}
            
            # Query Pinecone
            result = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict,
            )
            
            # Extract memories above threshold
            memories = []
            for match in result.matches:
                if match.score >= score_threshold:
                    memory_text = match.metadata.get("memory")
                    if memory_text:
                        memories.append(memory_text)
            
            logger.info(f"Retrieved {len(memories)} relevant memories for query: {query[:50]}...")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {str(e)}")
            return []  # Return empty list on error to avoid breaking chat flow
    
    def delete_memories_by_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete memories based on filter criteria
        
        Args:
            filter_dict (dict): Filter criteria for deletion
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.index.delete(filter=filter_dict)
            logger.info(f"Memories deleted with filter: {filter_dict}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memories: {str(e)}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index
        
        Returns:
            dict: Index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {}

# Create global memory manager instance
memory_manager = MemoryManager()

# Export functions for backward compatibility
def store_memory(text: str, metadata: Dict[str, Any]) -> str:
    """Store memory using the global memory manager"""
    return memory_manager.store_memory(text, metadata)

def get_relevant_memories(
    query: str, 
    user_filter: Optional[str] = None, 
    top_k: int = 5
) -> List[str]:
    """Retrieve memories using the global memory manager"""
    return memory_manager.get_relevant_memories(query, user_filter, top_k)

def delete_session_memories(session_id: str) -> bool:
    """Delete all memories for a specific session"""
    return memory_manager.delete_memories_by_filter({"session_id": {"$eq": session_id}})

def get_memory_stats() -> Dict[str, Any]:
    """Get memory database statistics"""
    return memory_manager.get_index_stats()

if __name__ == "__main__":
    # Test the memory manager
    try:
        # Test storing a memory
        test_metadata = {
            "user": "test_user",
            "type": "test",
            "source": "memory_manager_test"
        }
        
        memory_id = store_memory("This is a test memory", test_metadata)
        print(f"✅ Test memory stored: {memory_id}")
        
        # Test retrieving memories
        memories = get_relevant_memories("test memory", "test_user", 1)
        print(f"✅ Retrieved {len(memories)} memories")
        
        # Test stats
        stats = get_memory_stats()
        print(f"✅ Memory stats: {stats}")
        
    except Exception as e:
        print(f"❌ Memory manager test failed: {str(e)}")