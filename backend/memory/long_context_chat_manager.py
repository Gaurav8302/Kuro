"""
Long-Context Chat Manager for Llama 3.3 70B

This module provides an advanced chat manager that efficiently utilizes
the full 128K+ context window of long-context models while maintaining
optimal performance on resource-constrained servers.

Features:
- Hybrid memory system (recent + summarized)
- Dynamic context construction
- Token-aware prompt building
- Automatic memory summarization
- Efficient caching and cleanup

Version: 2025-07-30 - Optimized for Llama 3.3 70B 128K+ context
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

from utils.groq_client import GroqClient
from utils.kuro_prompt import build_kuro_prompt, sanitize_response
from utils.safety import validate_response, get_fallback_response
from memory.long_context_memory_manager import (
    get_long_context_memory_manager,
    LongContextMemoryManager,
    ContextConfig
)
from memory.chat_database import save_chat_to_db, get_chat_by_session
from memory.user_profile import get_user_name as get_profile_name, set_user_name

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LongContextChatManager:
    """
    Advanced chat manager for long-context models
    
    Efficiently manages conversations using hybrid memory approach:
    - Recent messages in full detail
    - Historical context through summaries
    - Semantic relevance for memory retrieval
    - Dynamic token management
    """
    
    def __init__(self, context_config: Optional[ContextConfig] = None):
        """Initialize the long-context chat manager"""
        try:
            self.groq_client = GroqClient()
            self.memory_manager = get_long_context_memory_manager()
            self.config = context_config or ContextConfig()
            
            # Performance tracking
            self.response_times = []
            self.token_usage_history = []
            
            logger.info("✅ Long-context chat manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize long-context chat manager: {e}")
            raise RuntimeError(f"Chat manager initialization failed: {e}")
    
    def extract_name(self, text: str) -> Optional[str]:
        """Extract user name from text using pattern matching"""
        import re
        
        patterns = [
            r"my name is (\w+)",
            r"i am (\w+)", 
            r"i'm (\w+)",
            r"this is (\w+)",
            r"call me (\w+)",
            r"i go by (\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).capitalize()
                logger.info(f"Extracted name: {name}")
                return name
        
        return None
    
    def get_user_name(self, user_id: str) -> Optional[str]:
        """Retrieve stored user name"""
        try:
            return get_profile_name(user_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to get user name: {e}")
            return None
    
    def store_user_name(self, user_id: str, name: str, context_message: str):
        """Store user name in profile and memory"""
        try:
            set_user_name(user_id, name)
            logger.info(f"✅ Stored user name: {name} for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to store user name: {e}")
    
    async def generate_long_context_response(
        self,
        user_message: str,
        context_prompt: str,
        token_usage: Dict[str, int],
        max_retries: int = 2
    ) -> str:
        """
        Generate AI response using long-context prompt
        
        Args:
            user_message: User's message
            context_prompt: Full context prompt
            token_usage: Token usage statistics
            max_retries: Maximum retry attempts
            
        Returns:
            AI response
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                start_time = datetime.now()
                
                # Generate response with extended context
                response = self.groq_client.generate_content(
                    prompt=context_prompt,
                    system_instruction="You are Kuro, a helpful AI assistant with access to extensive conversation history."
                )
                
                if not response:
                    logger.warning("⚠️ Empty response from Groq")
                    return get_fallback_response(user_message)
                
                # Sanitize response
                sanitized_response = sanitize_response(response)
                
                # Validate response safety
                is_valid, assessment = validate_response(sanitized_response, context_prompt)
                
                if is_valid:
                    # Track performance
                    response_time = (datetime.now() - start_time).total_seconds()
                    self.response_times.append(response_time)
                    self.token_usage_history.append(token_usage)
                    
                    # Keep only recent performance data
                    if len(self.response_times) > 100:
                        self.response_times = self.response_times[-50:]
                        self.token_usage_history = self.token_usage_history[-50:]
                    
                    logger.info(f"✅ Generated response in {response_time:.2f}s using {token_usage['total']} tokens")
                    return sanitized_response
                else:
                    logger.warning(f"⚠️ Unsafe response detected: {assessment.get('blocked_reasons', [])}")
                    
                    if retry_count >= max_retries:
                        return get_fallback_response(user_message)
                    
                    retry_count += 1
                    continue
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error generating response (attempt {retry_count + 1}): {error_msg}")
                
                # Handle rate limits
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    return self._get_rate_limit_message()
                
                if retry_count >= max_retries:
                    return get_fallback_response(user_message)
                
                retry_count += 1
                continue
        
        return get_fallback_response(user_message)
    
    def _get_rate_limit_message(self) -> str:
        """Get rate limit message"""
        return """🚧 **Development Mode Notice** 🚧

Hi! I'm currently using the Groq API for Llama 3.3 70B with extended context.

**We've hit the rate limit!** ⏰

This is temporary while we're optimizing the long-context system. Please try again in a few moments.

The new system can handle much longer conversations and remember more context, so it'll be worth the wait! 🚀

Thanks for your patience! 🙏"""
    
    async def chat_with_long_context(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Process chat message with long-context memory system
        
        Args:
            user_id: User identifier
            message: User's message
            session_id: Session identifier
            
        Returns:
            AI response
        """
        try:
            start_time = datetime.now()
            
            # 1. Handle name extraction and storage
            user_name = self.get_user_name(user_id) or "there"
            extracted_name = self.extract_name(message)
            
            if extracted_name and not self.get_user_name(user_id):
                self.store_user_name(user_id, extracted_name, message)
                user_name = extracted_name
                
                response = f"Nice to meet you, {user_name}! I'm Kuro, and I'll remember our conversation. How can I help you today?"
                
                # Store the introduction
                save_chat_to_db(user_id, message, response, session_id)
                return response
            
            # 2. Check if we need to summarize old messages
            try:
                chat_history = get_chat_by_session(session_id) if session_id else []
                if len(chat_history) > self.config.recent_messages_count + 20:
                    # Trigger background summarization
                    asyncio.create_task(
                        self.memory_manager.summarize_old_messages(user_id, session_id)
                    )
                    logger.info(f"🔄 Triggered background summarization for session {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to check session length: {e}")
            
            # 3. Build long-context prompt
            context_prompt, token_usage = await self.memory_manager.build_long_context_prompt(
                user_id=user_id,
                current_message=message,
                session_id=session_id or f"default_{user_id}",
                system_instruction=self._get_system_instruction()
            )
            
            # 4. Generate response with full context
            response = await self.generate_long_context_response(
                user_message=message,
                context_prompt=context_prompt,
                token_usage=token_usage
            )
            
            # 5. Store conversation
            save_chat_to_db(user_id, message, response, session_id)
            
            # 6. Trigger cleanup if needed (low frequency)
            if len(self.response_times) % 50 == 0:  # Every 50 responses
                asyncio.create_task(
                    self.memory_manager.cleanup_old_memories(user_id, days_old=60)
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Chat completed in {processing_time:.2f}s for {user_name} (user_id: {user_id})")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in chat processing: {e}")
            return "I apologize, but I encountered an error. Please try again."
    
    def _get_system_instruction(self) -> str:
        """Get system instruction for long-context model"""
        return """You are Kuro, a helpful and friendly AI assistant with access to extensive conversation history.

Key capabilities:
- You can remember and reference past conversations naturally
- You maintain context across long discussions
- You provide personalized responses based on user history
- You're conversational, engaging, and avoid repetition

Guidelines:
1. Use the conversation history to provide contextual responses
2. Reference past topics and preferences when relevant
3. Build naturally on previous discussions
4. Be helpful, friendly, and engaging
5. Avoid asking questions you already know the answers to
6. Provide specific, actionable advice when requested

Remember: You have access to both recent conversation and summarized historical context, so make use of this information to provide the best possible responses."""
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.response_times:
            return {'error': 'No performance data available'}
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        avg_tokens = sum(t['total'] for t in self.token_usage_history) / len(self.token_usage_history)
        
        return {
            'avg_response_time_seconds': round(avg_response_time, 2),
            'avg_tokens_per_request': round(avg_tokens),
            'total_requests': len(self.response_times),
            'max_tokens_used': max(t['total'] for t in self.token_usage_history),
            'min_tokens_used': min(t['total'] for t in self.token_usage_history),
            'context_efficiency': {
                'avg_recent_messages_tokens': round(
                    sum(t.get('recent_messages', 0) for t in self.token_usage_history) / len(self.token_usage_history)
                ),
                'avg_memory_chunks_tokens': round(
                    sum(t.get('memory_chunks', 0) for t in self.token_usage_history) / len(self.token_usage_history)
                ),
                'context_utilization_ratio': round(avg_tokens / self.config.max_total_tokens, 3)
            }
        }
    
    async def force_summarize_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Force summarization of a session (admin function)"""
        try:
            await self.memory_manager.summarize_old_messages(user_id, session_id)
            return {
                'success': True,
                'message': f'Session {session_id} summarized successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
_long_context_chat_manager = None

def get_long_context_chat_manager() -> LongContextChatManager:
    """Get global long-context chat manager instance"""
    global _long_context_chat_manager
    if _long_context_chat_manager is None:
        _long_context_chat_manager = LongContextChatManager()
    return _long_context_chat_manager

# Convenience function for backward compatibility
async def chat_with_long_context_memory(
    user_id: str,
    message: str,
    session_id: Optional[str] = None
) -> str:
    """Process chat message with long-context memory"""
    manager = get_long_context_chat_manager()
    return await manager.chat_with_long_context(user_id, message, session_id)

def get_chat_performance_stats() -> Dict[str, Any]:
    """Get chat performance statistics"""
    manager = get_long_context_chat_manager()
    return manager.get_performance_stats()

# Background task for periodic optimization
async def optimize_memory_system():
    """Background task to optimize memory system"""
    try:
        manager = get_long_context_chat_manager()
        
        # This would run periodically (e.g., via cron job or scheduler)
        # For now, it's a placeholder for future optimization tasks
        logger.info("🔄 Memory system optimization completed")
        
    except Exception as e:
        logger.error(f"❌ Error in memory optimization: {e}")

if __name__ == "__main__":
    # Test the long-context chat manager
    async def test_chat_manager():
        try:
            manager = get_long_context_chat_manager()
            
            # Test basic functionality
            response = await manager.chat_with_long_context(
                user_id="test_user",
                message="Hello, I'm testing the long-context system",
                session_id="test_session"
            )
            
            print(f"✅ Response: {response}")
            
            # Test performance stats
            stats = manager.get_performance_stats()
            print(f"✅ Performance stats: {stats}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Run test
    asyncio.run(test_chat_manager())
