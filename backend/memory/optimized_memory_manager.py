"""
Optimized Memory Manager for Groq LLaMA 3 70B (8K context limit)

This module provides an efficient memory system that:
1. Limits total prompt size to under 7000 tokens
2. Retrieves only top 3 relevant memory chunks from Pinecone
3. Summarizes long sessions and stores them in Pinecone
4. Passes only last 2 user-assistant messages to LLM
5. Uses sentence transformers for efficient embeddings
6. Includes periodic session summarization

Version: 2025-07-30 - Optimized for Groq LLaMA 3 70B
"""

import os
import logging
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

# Google Gemini for embeddings (free tier)
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class OptimizedMemoryManager:
    """
    Memory manager optimized for Groq LLaMA 3 70B's 8K context limit
    
    Key optimizations:
    - Token counting and limiting
    - Efficient memory retrieval (top 3 only)
    - Session summarization for long conversations
    - Minimal RAM usage
    """
    
    # Token limits
    MAX_TOTAL_TOKENS = 7000
    MAX_MEMORY_TOKENS = 2000
    MAX_HISTORY_TOKENS = 1500
    MAX_SYSTEM_TOKENS = 1000
    SUMMARIZATION_THRESHOLD = 10  # Messages before summarization
    
    def __init__(self):
        """Initialize the optimized memory manager"""
        # Initialize Google Gemini for embeddings
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for embeddings")
        
        genai.configure(api_key=api_key)
        self.embedding_model = "models/text-embedding-004"
        
        # Initialize Pinecone
        from pinecone import Pinecone
        pc_api_key = os.getenv("PINECONE_API_KEY")
        if not pc_api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
        
        try:
            self.pc = Pinecone(api_key=pc_api_key)
            index_name = os.getenv("PINECONE_INDEX_NAME", "my-chatbot-memory")
            self.index = self.pc.Index(index_name)
            logger.info("✅ Optimized memory manager initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone: {e}")
            raise
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text (str): Text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for English text
        return max(1, len(text) // 4)
    
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to approximate token limit
        
        Args:
            text (str): Text to truncate
            max_tokens (int): Maximum token count
            
        Returns:
            str: Truncated text
        """
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        
        # Truncate and add ellipsis
        truncated = text[:max_chars-3]
        # Try to break at word boundary
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding from Google Gemini with dimension matching
        
        Args:
            text (str): Text to embed
            
        Returns:
            List[float]: Embedding vector (384 dimensions)
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            embedding = result['embedding']
            
            # Ensure 384 dimensions for Pinecone compatibility
            if len(embedding) > 384:
                # Simple dimension reduction: take every 2nd element
                embedding = embedding[::2][:384]
            elif len(embedding) < 384:
                # Pad with zeros if needed
                embedding.extend([0.0] * (384 - len(embedding)))
            
            return embedding
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 384
    
    def store_memory_chunk(
        self, 
        text: str, 
        user_id: str,
        memory_type: str = "conversation",
        importance: float = 0.5,
        session_id: Optional[str] = None
    ) -> str:
        """
        Store a memory chunk in Pinecone
        
        Args:
            text (str): Text to store
            user_id (str): User identifier
            memory_type (str): Type of memory (conversation, summary, fact)
            importance (float): Importance score (0-1)
            session_id (Optional[str]): Session identifier
            
        Returns:
            str: Memory ID
        """
        try:
            # Generate embedding
            embedding = self.get_embedding(text)
            
            # Create memory ID
            memory_id = str(uuid.uuid4())
            
            # Prepare metadata
            metadata = {
                "text": text[:1000],  # Limit text length in metadata
                "user_id": user_id,
                "memory_type": memory_type,
                "importance": importance,
                "timestamp": datetime.now().isoformat(),
                "token_count": self.estimate_tokens(text)
            }
            
            if session_id:
                metadata["session_id"] = session_id
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[(memory_id, embedding, metadata)]
            )
            
            logger.info(f"✅ Stored memory chunk: {memory_id} ({memory_type})")
            return memory_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store memory chunk: {e}")
            return ""
    
    def retrieve_relevant_memories(
        self, 
        query: str, 
        user_id: str,
        top_k: int = 3,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-k most relevant memories from Pinecone
        
        Args:
            query (str): Query text
            user_id (str): User identifier
            top_k (int): Number of memories to retrieve (max 3)
            memory_types (Optional[List[str]]): Filter by memory types
            
        Returns:
            List[Dict]: Relevant memories with metadata
        """
        try:
            # Limit top_k to 3 for efficiency
            top_k = min(top_k, 3)
            
            # Generate query embedding
            query_embedding = self.get_embedding(query)
            
            # Build filter
            filter_dict = {"user_id": {"$eq": user_id}}
            if memory_types:
                filter_dict["memory_type"] = {"$in": memory_types}
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Process results
            memories = []
            total_tokens = 0
            
            for match in results.matches:
                if total_tokens >= self.MAX_MEMORY_TOKENS:
                    break
                
                metadata = match.metadata
                text = metadata.get("text", "")
                tokens = metadata.get("token_count", self.estimate_tokens(text))
                
                # Check if adding this memory would exceed token limit
                if total_tokens + tokens <= self.MAX_MEMORY_TOKENS:
                    memories.append({
                        "id": match.id,
                        "text": text,
                        "score": match.score,
                        "memory_type": metadata.get("memory_type", "unknown"),
                        "importance": metadata.get("importance", 0.5),
                        "timestamp": metadata.get("timestamp", ""),
                        "token_count": tokens
                    })
                    total_tokens += tokens
                else:
                    # Truncate text to fit remaining token budget
                    remaining_tokens = self.MAX_MEMORY_TOKENS - total_tokens
                    if remaining_tokens > 50:  # Only include if meaningful space left
                        truncated_text = self.truncate_to_tokens(text, remaining_tokens)
                        memories.append({
                            "id": match.id,
                            "text": truncated_text,
                            "score": match.score,
                            "memory_type": metadata.get("memory_type", "unknown"),
                            "importance": metadata.get("importance", 0.5),
                            "timestamp": metadata.get("timestamp", ""),
                            "token_count": remaining_tokens
                        })
                    break
            
            logger.info(f"✅ Retrieved {len(memories)} memories ({total_tokens} tokens)")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve memories: {e}")
            return []
    
    def get_recent_history(
        self, 
        session_id: str, 
        max_exchanges: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history (last N exchanges)
        
        Args:
            session_id (str): Session identifier
            max_exchanges (int): Maximum number of user-assistant exchanges
            
        Returns:
            List[Dict]: Recent conversation history
        """
        try:
            from memory.chat_database import get_chat_by_session
            
            # Get chat history from MongoDB
            chat_history = get_chat_by_session(session_id)
            if not chat_history:
                return []
            
            # Get last N exchanges (each exchange = user + assistant message)
            recent_messages = chat_history[-(max_exchanges * 2):]
            
            # Calculate tokens and truncate if necessary
            total_tokens = 0
            processed_history = []
            
            for msg in reversed(recent_messages):
                user_text = msg.get("user", "")
                assistant_text = msg.get("assistant", "")
                
                user_tokens = self.estimate_tokens(user_text)
                assistant_tokens = self.estimate_tokens(assistant_text)
                msg_tokens = user_tokens + assistant_tokens
                
                if total_tokens + msg_tokens <= self.MAX_HISTORY_TOKENS:
                    processed_history.insert(0, {
                        "user": user_text,
                        "assistant": assistant_text,
                        "timestamp": msg.get("timestamp", ""),
                        "token_count": msg_tokens
                    })
                    total_tokens += msg_tokens
                else:
                    # Try to fit truncated version
                    remaining_tokens = self.MAX_HISTORY_TOKENS - total_tokens
                    if remaining_tokens > 100:  # Only if meaningful space left
                        # Truncate both user and assistant messages proportionally
                        user_truncated = self.truncate_to_tokens(user_text, remaining_tokens // 2)
                        assistant_truncated = self.truncate_to_tokens(assistant_text, remaining_tokens // 2)
                        
                        processed_history.insert(0, {
                            "user": user_truncated,
                            "assistant": assistant_truncated,
                            "timestamp": msg.get("timestamp", ""),
                            "token_count": remaining_tokens
                        })
                    break
            
            logger.info(f"✅ Retrieved {len(processed_history)} recent messages ({total_tokens} tokens)")
            return processed_history
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent history: {e}")
            return []
    
    def should_summarize_session(self, session_id: str) -> bool:
        """
        Check if a session should be summarized
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if session should be summarized
        """
        try:
            from memory.chat_database import get_chat_by_session
            chat_history = get_chat_by_session(session_id)
            
            if not chat_history:
                return False
            
            return len(chat_history) >= self.SUMMARIZATION_THRESHOLD
            
        except Exception as e:
            logger.error(f"❌ Error checking summarization need: {e}")
            return False
    
    def summarize_session(
        self, 
        session_id: str, 
        user_id: str
    ) -> Optional[str]:
        """
        Summarize a long session and store summary in Pinecone
        
        Args:
            session_id (str): Session identifier
            user_id (str): User identifier
            
        Returns:
            Optional[str]: Summary text if successful
        """
        try:
            from memory.chat_database import get_chat_by_session
            from utils.groq_client import GroqClient
            
            # Get full chat history
            chat_history = get_chat_by_session(session_id)
            if not chat_history or len(chat_history) < self.SUMMARIZATION_THRESHOLD:
                return None
            
            # Prepare conversation text for summarization
            conversation_text = []
            for msg in chat_history[:-2]:  # Exclude last 2 messages (keep them as recent history)
                conversation_text.append(f"User: {msg.get('user', '')}")
                conversation_text.append(f"Assistant: {msg.get('assistant', '')}")
            
            full_conversation = "\n".join(conversation_text)
            
            # Generate summary using Groq
            groq_client = GroqClient()
            
            summary_prompt = f"""Please create a concise 1-2 sentence summary of this conversation that captures the key topics, user preferences, and important context:

Conversation:
{full_conversation[:3000]}  # Limit input to avoid token issues

Summary:"""

            summary = groq_client.generate_content(
                prompt=summary_prompt,
                system_instruction="You are a helpful assistant that creates concise, informative summaries of conversations. Focus on key topics, user preferences, and important context."
            )
            
            if summary:
                # Store summary in Pinecone as high-importance memory
                summary_id = self.store_memory_chunk(
                    text=f"Session Summary: {summary}",
                    user_id=user_id,
                    memory_type="summary",
                    importance=0.8,
                    session_id=session_id
                )
                
                logger.info(f"✅ Created session summary: {summary_id}")
                return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to summarize session: {e}")
            
        return None
    
    def build_optimized_context(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Tuple[str, Dict[str, int]]:
        """
        Build optimized context that fits within token limits
        
        Args:
            user_message (str): Current user message
            user_id (str): User identifier
            session_id (Optional[str]): Session identifier
            user_name (Optional[str]): User's name
            
        Returns:
            Tuple[str, Dict[str, int]]: Context string and token usage breakdown
        """
        try:
            token_usage = {
                "system": 0,
                "memories": 0,
                "history": 0,
                "user_message": self.estimate_tokens(user_message),
                "total": 0
            }
            
            context_parts = []
            
            # 1. Add user name if available (minimal tokens)
            if user_name:
                name_context = f"User's name: {user_name}"
                name_tokens = self.estimate_tokens(name_context)
                context_parts.append(name_context)
                token_usage["system"] += name_tokens
            
            # 2. Get relevant memories (max 3, token-limited)
            relevant_memories = self.retrieve_relevant_memories(
                query=user_message,
                user_id=user_id,
                top_k=3
            )
            
            if relevant_memories:
                memory_texts = []
                for memory in relevant_memories:
                    memory_texts.append(f"Context: {memory['text']}")
                    token_usage["memories"] += memory['token_count']
                
                context_parts.append("Relevant context:\n" + "\n".join(memory_texts))
            
            # 3. Get recent conversation history (last 2 exchanges)
            if session_id:
                recent_history = self.get_recent_history(session_id, max_exchanges=2)
                
                if recent_history:
                    history_texts = []
                    for msg in recent_history:
                        history_texts.append(f"Previous - User: {msg['user']}")
                        history_texts.append(f"Previous - Assistant: {msg['assistant']}")
                        token_usage["history"] += msg['token_count']
                    
                    context_parts.append("Recent conversation:\n" + "\n".join(history_texts))
            
            # 4. Build final context
            context = "\n\n".join(context_parts) if context_parts else ""
            
            # 5. Calculate total tokens and truncate if necessary
            context_tokens = self.estimate_tokens(context)
            token_usage["total"] = (
                token_usage["system"] + 
                token_usage["memories"] + 
                token_usage["history"] + 
                token_usage["user_message"]
            )
            
            # Reserve space for system prompt and response
            available_tokens = self.MAX_TOTAL_TOKENS - self.MAX_SYSTEM_TOKENS - 1000  # Reserve 1000 for response
            
            if token_usage["total"] > available_tokens:
                # Truncate context to fit
                max_context_tokens = available_tokens - token_usage["user_message"]
                context = self.truncate_to_tokens(context, max_context_tokens)
                token_usage["total"] = available_tokens
                logger.warning(f"⚠️ Context truncated to fit token limit ({available_tokens} tokens)")
            
            logger.info(f"✅ Built optimized context: {token_usage}")
            return context, token_usage
            
        except Exception as e:
            logger.error(f"❌ Failed to build optimized context: {e}")
            return "", {"total": 0, "system": 0, "memories": 0, "history": 0, "user_message": 0}
    
    def cleanup_old_memories(self, user_id: str, days_old: int = 30) -> int:
        """
        Clean up old, low-importance memories to free up space
        
        Args:
            user_id (str): User identifier
            days_old (int): Age threshold in days
            
        Returns:
            int: Number of memories cleaned up
        """
        try:
            from datetime import datetime, timedelta
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # Query old, low-importance memories
            # Note: This is a simplified approach - in production, you'd want to
            # implement a more sophisticated cleanup strategy
            
            logger.info(f"🧹 Memory cleanup for user {user_id} (older than {days_old} days)")
            # Implementation would depend on Pinecone's filtering capabilities
            # For now, just log the intent
            
            return 0  # Placeholder
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup memories: {e}")
            return 0


# Global instance
optimized_memory_manager = OptimizedMemoryManager()


# Convenience functions for backward compatibility
def store_optimized_memory(
    text: str, 
    user_id: str,
    memory_type: str = "conversation",
    importance: float = 0.5,
    session_id: Optional[str] = None
) -> str:
    """Store memory using optimized manager"""
    return optimized_memory_manager.store_memory_chunk(
        text=text,
        user_id=user_id,
        memory_type=memory_type,
        importance=importance,
        session_id=session_id
    )


def get_optimized_memories(
    query: str, 
    user_id: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """Retrieve memories using optimized manager"""
    return optimized_memory_manager.retrieve_relevant_memories(
        query=query,
        user_id=user_id,
        top_k=top_k
    )


def build_optimized_context(
    user_message: str,
    user_id: str,
    session_id: Optional[str] = None,
    user_name: Optional[str] = None
) -> Tuple[str, Dict[str, int]]:
    """Build optimized context using optimized manager"""
    return optimized_memory_manager.build_optimized_context(
        user_message=user_message,
        user_id=user_id,
        session_id=session_id,
        user_name=user_name
    )


def check_and_summarize_session(session_id: str, user_id: str) -> Optional[str]:
    """Check if session needs summarization and do it if needed"""
    if optimized_memory_manager.should_summarize_session(session_id):
        return optimized_memory_manager.summarize_session(session_id, user_id)
    return None
