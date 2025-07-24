"""
Enhanced Memory Management Module

This module handles the storage and retrieval of user memories using Pinecone
vector database with cross-session continuity and intelligent categorization.

Features:
- Vector embedding using sentence transformers
- Pinecone vector database integration
- User-isolated memory storage with cross-session continuity
- Semantic similarity search with importance scoring
- Memory metadata management and categorization
- Local caching for performance optimization
"""

import os
import logging
from uuid import uuid4
from datetime import datetime, timedelta
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

class EnhancedMemoryManager:
    """
    Enhanced memory management class for handling vector storage and retrieval
    with cross-session continuity and intelligent categorization.
    """
    
    def __init__(self):
        """Initialize the memory manager with Pinecone and embedding model"""
        self._initialize_pinecone()
        self._initialize_embedding_model()
        self._memory_cache = {}  # Local cache for frequently accessed memories
        self._user_contexts = {}  # User context tracking
    
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
    
    def _calculate_importance_score(self, text: str, metadata: Dict[str, Any]) -> float:
        """
        Calculate importance score based on content and context
        
        Args:
            text (str): Memory text content
            metadata (dict): Memory metadata
            
        Returns:
            float: Importance score (0.0 to 1.0)
        """
        base_score = metadata.get("importance", 0.5)
        
        # Boost importance for user profile information
        if "user_profile" in self._categorize_memory(text, metadata):
            base_score += 0.3
        
        # Boost for explicit importance indicators
        text_lower = text.lower()
        if any(word in text_lower for word in ["important", "remember", "key", "crucial"]):
            base_score += 0.2
        
        # Boost for questions or clarifications
        if "?" in text or any(word in text_lower for word in ["what", "how", "why", "when", "where"]):
            base_score += 0.1
        
        return min(1.0, base_score)  # Cap at 1.0
    
    def store_memory(self, text: str, metadata: Dict[str, Any], importance: Optional[float] = None) -> str:
        """
        Store a memory in the vector database with enhanced metadata and importance scoring
        
        Args:
            text (str): Memory text content
            metadata (dict): Additional metadata for the memory
            importance (float, optional): Manual importance score (0.0 to 1.0)
            
        Returns:
            str: Unique ID of the stored memory
        """
        try:
            # Validate required metadata
            if "user" not in metadata:
                raise ValueError("Missing 'user' field in metadata. Cannot store memory without user ID.")
            
            # Calculate importance score if not provided
            if importance is None:
                importance = self._calculate_importance_score(text, metadata)
            
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
                "timestamp": enhanced_metadata["timestamp"],
                "category": enhanced_metadata["memory_type"]
            })
            
            # Sort by importance and keep top memories
            self._memory_cache[user_id].sort(key=lambda x: x["importance"], reverse=True)
            self._memory_cache[user_id] = self._memory_cache[user_id][:20]
            
            logger.info(f"✅ Memory stored successfully: {memory_id[:8]}... (importance: {importance:.2f}, type: {enhanced_metadata['memory_type']})")
            return memory_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store memory: {str(e)}")
            raise RuntimeError(f"Memory storage failed: {str(e)}")
    
    def get_relevant_memories(
        self, 
        query: str, 
        user_filter: Optional[str] = None, 
        top_k: int = 8,
        score_threshold: float = 0.5,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories based on a query with enhanced filtering
        
        Args:
            query (str): Query text for similarity search
            user_filter (str, optional): Filter memories by user ID
            top_k (int): Maximum number of memories to retrieve
            score_threshold (float): Minimum similarity score threshold
            memory_types (List[str], optional): Filter by memory types
            
        Returns:
            List[Dict]: List of relevant memories with metadata
        """
        try:
            # Check cache first for user profile memories
            if user_filter and user_filter in self._memory_cache:
                cached_memories = self._memory_cache[user_filter]
                profile_memories = [m for m in cached_memories if m.get("category") == "user_profile"]
                if profile_memories and any(keyword in query.lower() for keyword in ["name", "who", "profile"]):
                    logger.info(f"Using cached profile memories for user {user_filter}")
                    return [{
                        "text": m["text"],
                        "importance": m["importance"],
                        "category": m["category"],
                        "timestamp": m["timestamp"]
                    } for m in profile_memories[:2]]
            
            # Generate query embedding
            query_vector = self.embed_text(query)
            
            # Build filter dictionary
            filter_dict = {}
            if user_filter:
                filter_dict["user"] = {"$eq": user_filter}
            if memory_types:
                filter_dict["memory_type"] = {"$in": memory_types}
            
            # Query Pinecone
            result = self.index.query(
                vector=query_vector,
                top_k=top_k * 2,  # Get more results to filter better
                include_metadata=True,
                filter=filter_dict,
            )
            
            # Process and rank results
            memories = []
            seen_texts = set()  # Avoid duplicates
            
            for match in result.matches:
                if match.score >= score_threshold:
                    memory_text = match.metadata.get("memory_text", "")
                    if memory_text and memory_text not in seen_texts:
                        seen_texts.add(memory_text)
                        
                        # Update access count
                        self._update_memory_access(match.id, match.metadata)
                        
                        memories.append({
                            "text": memory_text,
                            "score": match.score,
                            "importance": match.metadata.get("importance", 0.5),
                            "category": match.metadata.get("memory_type", "general"),
                            "timestamp": match.metadata.get("timestamp", ""),
                            "session_id": match.metadata.get("session_id", ""),
                            "access_count": match.metadata.get("access_count", 0)
                        })
            
            # Sort by combined score (similarity + importance)
            memories.sort(key=lambda x: (x["score"] * 0.7 + x["importance"] * 0.3), reverse=True)
            memories = memories[:top_k]
            
            logger.info(f"Retrieved {len(memories)} relevant memories for query: '{query[:50]}...' (user: {user_filter})")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {str(e)}")
            return []  # Return empty list on error to avoid breaking chat flow
    
    def _update_memory_access(self, memory_id: str, metadata: Dict[str, Any]):
        """Update memory access count and timestamp"""
        try:
            updated_metadata = {
                **metadata,
                "access_count": metadata.get("access_count", 0) + 1,
                "last_accessed": datetime.utcnow().isoformat()
            }
            
            # Re-embed the text and update
            memory_text = metadata.get("memory_text", "")
            if memory_text:
                embedding = self.embed_text(memory_text)
                self.index.upsert(vectors=[
                    {
                        "id": memory_id,
                        "values": embedding,
                        "metadata": updated_metadata
                    }
                ])
                
        except Exception as e:
            logger.error(f"Failed to update memory access: {str(e)}")
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user context from all memories
        
        Args:
            user_id (str): User identifier
            
        Returns:
            Dict: User context including name, preferences, goals, etc.
        """
        try:
            context = {
                "name": None,
                "preferences": [],
                "goals": [],
                "skills": [],
                "key_facts": [],
                "conversation_history": []
            }
            
            # Get all memory types for the user
            for memory_type in ["user_profile", "preferences", "goals", "skills", "key_information"]:
                memories = self.get_relevant_memories(
                    query=memory_type,
                    user_filter=user_id,
                    top_k=5,
                    memory_types=[memory_type]
                )
                
                if memory_type == "user_profile":
                    for memory in memories:
                        if "name" in memory["text"].lower():
                            # Extract name from memory
                            import re
                            name_match = re.search(r"my name is (\w+)|i am (\w+)|call me (\w+)", memory["text"].lower())
                            if name_match:
                                context["name"] = name_match.group(1) or name_match.group(2) or name_match.group(3)
                                context["name"] = context["name"].capitalize()
                                break
                
                elif memory_type == "preferences":
                    context["preferences"] = [m["text"] for m in memories[:3]]
                elif memory_type == "goals":
                    context["goals"] = [m["text"] for m in memories[:3]]
                elif memory_type == "skills":
                    context["skills"] = [m["text"] for m in memories[:3]]
                elif memory_type == "key_information":
                    context["key_facts"] = [m["text"] for m in memories[:3]]
            
            self._user_contexts[user_id] = context
            return context
            
        except Exception as e:
            logger.error(f"Failed to get user context: {str(e)}")
            return {"name": None, "preferences": [], "goals": [], "skills": [], "key_facts": []}
    
    def cleanup_old_memories(self, user_id: str, days_threshold: int = 30):
        """
        Clean up old, low-importance memories to maintain performance
        
        Args:
            user_id (str): User identifier
            days_threshold (int): Delete memories older than this many days
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            cutoff_iso = cutoff_date.isoformat()
            
            # Delete old, low-importance memories
            filter_dict = {
                "user": {"$eq": user_id},
                "timestamp": {"$lt": cutoff_iso},
                "importance": {"$lt": 0.3}
            }
            
            self.index.delete(filter=filter_dict)
            logger.info(f"Cleaned up old memories for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup memories: {str(e)}")

# Create global instance
memory_manager = EnhancedMemoryManager()

# Export functions for backward compatibility
def store_memory(text: str, metadata: Dict[str, Any], importance: Optional[float] = None) -> str:
    """Store memory using the global memory manager"""
    return memory_manager.store_memory(text, metadata, importance)

def get_relevant_memories(
    query: str, 
    user_filter: Optional[str] = None, 
    top_k: int = 8
) -> List[str]:
    """Get relevant memories using the global memory manager (backward compatible)"""
    memories = memory_manager.get_relevant_memories(query, user_filter, top_k)
    return [m["text"] for m in memories]

def get_relevant_memories_detailed(
    query: str, 
    user_filter: Optional[str] = None, 
    top_k: int = 8,
    memory_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Get detailed relevant memories using the global memory manager"""
    return memory_manager.get_relevant_memories(query, user_filter, top_k, memory_types=memory_types)

if __name__ == "__main__":
    # Test the enhanced memory manager
    try:
        # Test memory storage
        test_metadata = {"user": "test_user", "session_id": "test_session"}
        memory_id = store_memory("My name is Alice and I love programming", test_metadata)
        print(f"✅ Stored memory: {memory_id}")
        
        # Test memory retrieval
        memories = get_relevant_memories("name programming", "test_user")
        print(f"✅ Retrieved memories: {memories}")
        
        # Test user context
        context = memory_manager.get_user_context("test_user")
        print(f"✅ User context: {context}")
        
    except Exception as e:
        print(f"❌ Enhanced memory manager test failed: {str(e)}")
