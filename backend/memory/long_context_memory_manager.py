"""
Long-Context Memory Manager for LLaMA 3.3 70B (128K context)

This module implements a sophisticated two-tier memory system optimized for
long-context models like LLaMA 3.3 70B with 128K token capacity.

Architecture:
1. Short-Term Memory (STM): Last 3-5 user/assistant message pairs
2. Long-Term Memory (LTM): Compressed session summaries stored in vector DB
3. Dynamic Context Assembly: Combines STM + relevant LTM for each request
4. Automatic Session Summarization: Background compression of old conversations
5. Token-Aware Prompt Building: Ensures prompts stay under 120K tokens

Memory Optimization:
- Lightweight JSON structures for runtime data
- External storage for embeddings and summaries
- Streaming/generator patterns to minimize RAM usage
- Lazy loading of historical data

Version: 2025-07-30 - Optimized for LLaMA 3.3 70B 128K context
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Generator
from datetime import datetime, timedelta
import hashlib
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import asyncio

from utils.groq_client import GroqClient
from utils.token_utils import estimate_tokens, truncate_text
from memory.chat_database import get_chat_by_session, save_chat_to_db
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Gemini for embeddings (free tier)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@dataclass
class ConversationSummary:
    """Structured conversation summary for efficient storage"""
    session_id: str
    user_id: str
    summary: str
    key_topics: List[str]
    user_preferences: List[str]
    important_facts: List[str]
    timestamp: str
    message_count: int
    tokens_original: int
    tokens_compressed: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        """Create from dictionary"""
        return cls(**data)

class LongContextMemoryManager:
    """
    Advanced memory manager for long-context LLaMA 3.3 70B model
    
    Implements a two-tier memory system:
    - Short-term: Recent messages (full detail)
    - Long-term: Summarized conversations (compressed)
    
    Features:
    - Token-aware context building (stays under 120K tokens)
    - Automatic session summarization
    - Semantic relevance search for LTM retrieval
    - Memory decay and cleanup
    - RAM optimization for 512MB servers
    """
    
    # Configuration constants
    MAX_TOTAL_TOKENS = 120000  # Reserve 11K for response
    MAX_CONTEXT_TOKENS = 100000  # Reserve 20K buffer for safety
    STM_MESSAGE_LIMIT = 5  # Last N message pairs in short-term memory
    LTM_RETRIEVAL_LIMIT = 3  # Max summaries to retrieve from long-term memory
    SUMMARIZATION_THRESHOLD = 4  # Summarize sessions with 4+ messages (reduced for better memory)
    
    def __init__(self):
        """Initialize the long-context memory manager"""
        self.groq_client = GroqClient()
        self.pinecone_index = self._initialize_pinecone()
        self.session_cache = {}  # Lightweight cache for active sessions
        
        logger.info("✅ Long-context memory manager initialized for LLaMA 3.3 70B")
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection for vector storage"""
        try:
            import pinecone
            from pinecone import Pinecone
            
            # Initialize Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            index_name = os.getenv("PINECONE_INDEX_NAME", "kuro-memory")
            
            # Connect to existing index
            index = pc.Index(index_name)
            logger.info(f"✅ Connected to Pinecone index: {index_name}")
            return index
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone: {e}")
            raise RuntimeError(f"Pinecone initialization failed: {e}")
    
    def get_short_term_memory(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get recent messages for short-term memory (last N pairs)
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of recent message dictionaries
        """
        try:
            # Check cache first
            if session_id in self.session_cache:
                return self.session_cache[session_id][-self.STM_MESSAGE_LIMIT * 2:]
            
            # Load from database (only recent messages)
            chat_history = get_chat_by_session(session_id)
            if not chat_history:
                return []
            
            # Get last N user/assistant pairs (N*2 messages total)
            recent_messages = chat_history[-(self.STM_MESSAGE_LIMIT * 2):]
            
            # Cache for future use (lightweight)
            self.session_cache[session_id] = recent_messages
            
            logger.info(f"📋 Retrieved {len(recent_messages)} STM messages for session {session_id}")
            return recent_messages
            
        except Exception as e:
            logger.error(f"❌ Error retrieving STM: {e}")
            return []
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using Gemini (free tier)
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            # Use Gemini's embedding model (free tier)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            
            embedding = result['embedding']
            
            # Ensure consistent dimensions for Pinecone
            if len(embedding) > 384:
                # Simple dimension reduction for compatibility
                embedding = embedding[::2][:384]
            elif len(embedding) < 384:
                # Pad if too short
                embedding.extend([0.0] * (384 - len(embedding)))
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return [0.0] * 384  # Return zero vector as fallback
    
    def summarize_chat(self, session_messages: List[Dict[str, str]]) -> ConversationSummary:
        """
        Summarize a full chat session using LLaMA 3.3 70B
        
        This function takes a complete session and creates a compressed summary
        that preserves key information while drastically reducing token count.
        
        Args:
            session_messages: List of message dictionaries
            
        Returns:
            ConversationSummary object with compressed information
        """
        try:
            if len(session_messages) < self.SUMMARIZATION_THRESHOLD:
                raise ValueError(f"Session too short for summarization ({len(session_messages)} < {self.SUMMARIZATION_THRESHOLD})")
            
            # Extract session metadata
            session_id = session_messages[0].get('session_id', 'unknown')
            user_id = session_messages[0].get('user_id', 'unknown')
            
            # Build conversation text for summarization
            conversation_text = self._build_conversation_text(session_messages)
            original_tokens = estimate_tokens(conversation_text)
            
            # Create summarization prompt
            summarization_prompt = f"""Please analyze this conversation and create a comprehensive summary. Focus on:

1. Main topics discussed
2. User preferences and interests mentioned
3. Important facts or information shared
4. Key decisions or conclusions reached
5. User's goals or objectives

CONVERSATION:
{conversation_text}

Provide your response in this exact JSON format:
{{
    "summary": "Comprehensive summary of the conversation (2-3 paragraphs)",
    "key_topics": ["topic1", "topic2", "topic3"],
    "user_preferences": ["preference1", "preference2"],
    "important_facts": ["fact1", "fact2", "fact3"]
}}"""
            
            # Generate summary using LLaMA 3.3 70B
            response = self.groq_client.generate_content(
                prompt=summarization_prompt,
                system_instruction="You are an expert at analyzing conversations and extracting key information. Always respond with valid JSON."
            )
            
            # Parse JSON response
            try:
                summary_data = json.loads(response.strip())
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                summary_data = {
                    "summary": response[:500],
                    "key_topics": [],
                    "user_preferences": [],
                    "important_facts": []
                }
            
            # Create structured summary
            summary = ConversationSummary(
                session_id=session_id,
                user_id=user_id,
                summary=summary_data.get("summary", ""),
                key_topics=summary_data.get("key_topics", []),
                user_preferences=summary_data.get("user_preferences", []),
                important_facts=summary_data.get("important_facts", []),
                timestamp=datetime.now().isoformat(),
                message_count=len(session_messages),
                tokens_original=original_tokens,
                tokens_compressed=estimate_tokens(summary_data.get("summary", ""))
            )
            
            # Store in vector database
            self._store_summary_in_vector_db(summary)
            
            logger.info(f"✅ Summarized session {session_id}: {original_tokens} → {summary.tokens_compressed} tokens")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Chat summarization failed: {e}")
            # Return minimal summary as fallback
            return ConversationSummary(
                session_id=session_messages[0].get('session_id', 'unknown'),
                user_id=session_messages[0].get('user_id', 'unknown'),
                summary="Session summary unavailable due to processing error",
                key_topics=[],
                user_preferences=[],
                important_facts=[],
                timestamp=datetime.now().isoformat(),
                message_count=len(session_messages),
                tokens_original=0,
                tokens_compressed=0
            )
    
    def _build_conversation_text(self, messages: List[Dict[str, str]]) -> str:
        """
        Build formatted conversation text for summarization
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted conversation string
        """
        conversation_lines = []
        
        for msg in messages:
            role = "User" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', msg.get('message', ''))
            timestamp = msg.get('timestamp', '')
            
            if content:
                line = f"{role}: {content}"
                if timestamp:
                    line += f" [{timestamp}]"
                conversation_lines.append(line)
        
        return "\n\n".join(conversation_lines)
    
    def _store_summary_in_vector_db(self, summary: ConversationSummary):
        """
        Store conversation summary in Pinecone vector database
        
        Args:
            summary: ConversationSummary object to store
        """
        try:
            # Create searchable text from summary
            searchable_text = f"{summary.summary} {' '.join(summary.key_topics)} {' '.join(summary.user_preferences)} {' '.join(summary.important_facts)}"
            
            # Generate embedding
            embedding = self.generate_embedding(searchable_text)
            
            # Create unique ID for the summary
            summary_id = f"summary_{summary.session_id}_{hashlib.md5(summary.timestamp.encode()).hexdigest()[:8]}"
            
            # Prepare metadata for Pinecone
            metadata = {
                "user_id": summary.user_id,
                "session_id": summary.session_id,
                "type": "conversation_summary",
                "timestamp": summary.timestamp,
                "message_count": summary.message_count,
                "tokens_original": summary.tokens_original,
                "tokens_compressed": summary.tokens_compressed,
                "summary_text": summary.summary[:1000],  # Truncate for metadata limits
                "key_topics": json.dumps(summary.key_topics),
                "user_preferences": json.dumps(summary.user_preferences),
                "important_facts": json.dumps(summary.important_facts)
            }
            
            # Store in Pinecone
            self.pinecone_index.upsert([
                (summary_id, embedding, metadata)
            ])
            
            logger.info(f"✅ Stored summary {summary_id} in vector DB")
            
        except Exception as e:
            logger.error(f"❌ Failed to store summary in vector DB: {e}")
    
    def retrieve_relevant_summaries(self, user_id: str, current_query: str) -> List[ConversationSummary]:
        """
        Retrieve relevant conversation summaries from long-term memory
        
        Uses semantic search to find the most relevant past conversations
        based on the current query context.
        
        Args:
            user_id: User identifier for isolation
            current_query: Current conversation context for relevance matching
            
        Returns:
            List of relevant ConversationSummary objects
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(current_query)
            
            # Search in Pinecone with user filter
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=self.LTM_RETRIEVAL_LIMIT,
                include_metadata=True,
                filter={
                    "user_id": user_id,
                    "type": "conversation_summary"
                }
            )
            
            # Convert results to ConversationSummary objects
            summaries = []
            for match in results.matches:
                try:
                    metadata = match.metadata
                    summary = ConversationSummary(
                        session_id=metadata.get("session_id", ""),
                        user_id=metadata.get("user_id", ""),
                        summary=metadata.get("summary_text", ""),
                        key_topics=json.loads(metadata.get("key_topics", "[]")),
                        user_preferences=json.loads(metadata.get("user_preferences", "[]")),
                        important_facts=json.loads(metadata.get("important_facts", "[]")),
                        timestamp=metadata.get("timestamp", ""),
                        message_count=metadata.get("message_count", 0),
                        tokens_original=metadata.get("tokens_original", 0),
                        tokens_compressed=metadata.get("tokens_compressed", 0)
                    )
                    summaries.append(summary)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse summary from metadata: {e}")
                    continue
            
            logger.info(f"🔍 Retrieved {len(summaries)} relevant summaries for user {user_id}")
            return summaries
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve relevant summaries: {e}")
            return []
    
    def build_context(self, user_id: str, session_id: str, current_message: str) -> Tuple[str, Dict[str, int]]:
        """
        Build optimized context for long-context model
        
        Combines short-term memory (recent messages) with relevant long-term
        memory (conversation summaries) to create the optimal prompt context.
        
        Args:
            user_id: User identifier
            session_id: Current session identifier
            current_message: User's current message
            
        Returns:
            Tuple of (context_string, token_usage_breakdown)
        """
        try:
            # 1. Get short-term memory (recent messages)
            stm_messages = self.get_short_term_memory(session_id)
            stm_text = self._format_stm_messages(stm_messages)
            stm_tokens = estimate_tokens(stm_text)
            
            # 2. Retrieve relevant long-term memory summaries
            ltm_summaries = self.retrieve_relevant_summaries(user_id, current_message)
            ltm_text = self._format_ltm_summaries(ltm_summaries)
            ltm_tokens = estimate_tokens(ltm_text)
            
            # 3. Build system instructions
            system_text = self._build_system_instructions(user_id)
            system_tokens = estimate_tokens(system_text)
            
            # 4. Current message tokens
            message_tokens = estimate_tokens(current_message)
            
            # 5. Calculate total tokens and apply limits
            total_tokens = system_tokens + ltm_tokens + stm_tokens + message_tokens
            
            # 6. Apply token limits with intelligent truncation
            if total_tokens > self.MAX_CONTEXT_TOKENS:
                logger.warning(f"⚠️ Context exceeds limit ({total_tokens} > {self.MAX_CONTEXT_TOKENS}), applying truncation")
                
                # Priority: System > Current Message > STM > LTM
                available_tokens = self.MAX_CONTEXT_TOKENS - system_tokens - message_tokens
                
                # Truncate STM if needed
                if stm_tokens > available_tokens // 2:
                    stm_text = truncate_text(stm_text, available_tokens // 2)
                    stm_tokens = estimate_tokens(stm_text)
                
                # Truncate LTM with remaining tokens
                remaining_tokens = available_tokens - stm_tokens
                if ltm_tokens > remaining_tokens:
                    ltm_text = truncate_text(ltm_text, remaining_tokens)
                    ltm_tokens = estimate_tokens(ltm_text)
            
            # 7. Assemble final context
            context_parts = []
            
            if system_text:
                context_parts.append(f"=== SYSTEM CONTEXT ===\n{system_text}")
            
            if ltm_text:
                context_parts.append(f"=== RELEVANT PAST CONVERSATIONS ===\n{ltm_text}")
            
            if stm_text:
                context_parts.append(f"=== RECENT CONVERSATION ===\n{stm_text}")
            
            final_context = "\n\n".join(context_parts)
            final_tokens = estimate_tokens(final_context)
            
            # Token usage breakdown for monitoring
            token_usage = {
                "system": system_tokens,
                "long_term_memory": ltm_tokens,
                "short_term_memory": stm_tokens,
                "current_message": message_tokens,
                "total_context": final_tokens,
                "summaries_retrieved": len(ltm_summaries),
                "stm_messages": len(stm_messages)
            }
            
            logger.info(f"🔧 Built context: {final_tokens} tokens ({len(ltm_summaries)} LTM summaries, {len(stm_messages)} STM messages)")
            return final_context, token_usage
            
        except Exception as e:
            logger.error(f"❌ Context building failed: {e}")
            # Return minimal context as fallback
            return f"Current message: {current_message}", {"total_context": estimate_tokens(current_message)}
    
    def _format_stm_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format short-term memory messages for context"""
        if not messages:
            return ""
        
        formatted_messages = []
        for msg in messages:
            role = "User" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', msg.get('message', ''))
            if content:
                formatted_messages.append(f"{role}: {content}")
        
        return "\n".join(formatted_messages)
    
    def _format_ltm_summaries(self, summaries: List[ConversationSummary]) -> str:
        """Format long-term memory summaries for context"""
        if not summaries:
            return ""
        
        formatted_summaries = []
        for i, summary in enumerate(summaries, 1):
            summary_text = f"Past Conversation {i}:\n{summary.summary}"
            
            if summary.key_topics:
                summary_text += f"\nTopics: {', '.join(summary.key_topics)}"
            
            if summary.user_preferences:
                summary_text += f"\nUser Preferences: {', '.join(summary.user_preferences)}"
            
            if summary.important_facts:
                summary_text += f"\nKey Facts: {', '.join(summary.important_facts)}"
            
            formatted_summaries.append(summary_text)
        
        return "\n\n".join(formatted_summaries)
    
    def _build_system_instructions(self, user_id: str) -> str:
        """Build system instructions for the current user"""
        try:
            # Get user profile information
            from memory.user_profile import get_user_name
            user_name = get_user_name(user_id) or "User"
            
            system_text = f"""You are Kuro, a helpful AI assistant talking to {user_name}.

Key Instructions:
1. Use the provided conversation history and summaries to maintain context across sessions
2. Reference relevant information from past conversations when appropriate
3. Be conversational and personalized based on the user's preferences and history
4. If asked about something discussed previously, refer to the relevant past conversation
5. Maintain consistency with previous responses and established facts

User Context: You are chatting with {user_name}. Use past conversation summaries and recent messages to provide contextually relevant responses."""
            
            return system_text
            
        except Exception as e:
            logger.error(f"❌ Failed to build system instructions: {e}")
            return "You are Kuro, a helpful AI assistant."
    
    def chat_with_long_context_memory(
        self, 
        user_id: str, 
        message: str, 
        session_id: Optional[str] = None
    ) -> str:
        """
        Main chat function with long-context memory integration
        
        This is the primary interface for generating responses using the
        two-tier memory system optimized for LLaMA 3.3 70B.
        
        Args:
            user_id: User identifier
            message: User's message
            session_id: Optional session identifier
            
        Returns:
            AI response string
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Build optimized context
            context, token_usage = self.build_context(user_id, session_id, message)
            
            # Generate response using LLaMA 3.3 70B with full context
            response = self.groq_client.generate_content(
                prompt=f"{context}\n\nUser: {message}\n\nAssistant:",
                system_instruction="You are Kuro, a helpful AI assistant. Use the provided context to give relevant, personalized responses."
            )
            
            # Store the exchange in database
            save_chat_to_db(user_id, message, response, session_id)
            
            # Update session cache
            if session_id not in self.session_cache:
                self.session_cache[session_id] = []
            
            self.session_cache[session_id].extend([
                {"role": "user", "content": message, "session_id": session_id, "user_id": user_id},
                {"role": "assistant", "content": response, "session_id": session_id, "user_id": user_id}
            ])
            
            # Keep cache lightweight (only recent messages)
            if len(self.session_cache[session_id]) > self.STM_MESSAGE_LIMIT * 2:
                self.session_cache[session_id] = self.session_cache[session_id][-(self.STM_MESSAGE_LIMIT * 2):]
            
            # Log successful interaction
            logger.info(f"✅ Generated response for {user_id} using {token_usage['total_context']} context tokens")
            return response
            
        except Exception as e:
            logger.error(f"❌ Chat generation failed: {e}")
            return "I apologize, but I encountered an error while processing your message. Please try again."
    
    def should_summarize_session(self, session_id: str) -> bool:
        """
        Check if a session should be summarized
        
        Args:
            session_id: Session to check
            
        Returns:
            True if session should be summarized
        """
        try:
            # Check if already summarized
            summary_id = f"summary_{session_id}"
            existing = self.pinecone_index.query(
                vector=[0.0] * 384,  # Dummy vector for metadata search
                top_k=1,
                include_metadata=True,
                filter={"session_id": session_id, "type": "conversation_summary"}
            )
            
            if existing.matches:
                return False  # Already summarized
            
            # Check message count
            chat_history = get_chat_by_session(session_id)
            return len(chat_history) >= self.SUMMARIZATION_THRESHOLD
            
        except Exception as e:
            logger.error(f"❌ Error checking summarization status: {e}")
            return False
    
    def cleanup_old_memories(self, user_id: str, days_old: int = 90) -> int:
        """
        Clean up old conversation summaries to manage storage
        
        Args:
            user_id: User identifier
            days_old: Age threshold in days
            
        Returns:
            Number of memories cleaned up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # Query old summaries
            # Note: This would need a more sophisticated implementation
            # depending on Pinecone's filtering capabilities
            logger.info(f"🧹 Memory cleanup requested for user {user_id} (>{days_old} days)")
            
            # For now, return 0 as this requires more complex Pinecone operations
            return 0
            
        except Exception as e:
            logger.error(f"❌ Memory cleanup failed: {e}")
            return 0

# Global instance for use throughout the application
long_context_memory_manager = LongContextMemoryManager()

def chat_with_long_context_memory(user_id: str, message: str, session_id: Optional[str] = None) -> str:
    """
    Convenience function for chat with long-context memory
    
    Args:
        user_id: User identifier
        message: User's message
        session_id: Optional session identifier
        
    Returns:
        AI response string
    """
    return long_context_memory_manager.chat_with_long_context_memory(user_id, message, session_id)

def summarize_session_background(session_id: str) -> Optional[ConversationSummary]:
    """
    Background function to summarize a session
    
    Args:
        session_id: Session to summarize
        
    Returns:
        ConversationSummary if successful, None otherwise
    """
    try:
        if not long_context_memory_manager.should_summarize_session(session_id):
            return None
        
        # Get full session messages
        messages = get_chat_by_session(session_id)
        if not messages:
            return None
        
        # Generate summary
        return long_context_memory_manager.summarize_chat(messages)
        
    except Exception as e:
        logger.error(f"❌ Background summarization failed for {session_id}: {e}")
        return None

if __name__ == "__main__":
    # Test the long-context memory system
    try:
        test_user_id = "test_user_123"
        test_message = "Hello, I'm interested in learning about machine learning"
        
        response = chat_with_long_context_memory(test_user_id, test_message)
        print(f"✅ Test response: {response}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
