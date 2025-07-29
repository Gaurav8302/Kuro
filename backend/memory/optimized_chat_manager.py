"""
Optimized Chat Manager for Groq LLaMA 3 70B

This module provides an optimized chat management system that:
1. Enforces 7000 token limit for total context
2. Uses only top 3 relevant memories from Pinecone
3. Includes only last 2 user-assistant message exchanges
4. Automatically summarizes long sessions
5. Optimizes memory usage and performance

Version: 2025-07-30 - Optimized for Groq LLaMA 3 70B 8K context
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv

# Import optimized components
from memory.optimized_memory_manager import (
    optimized_memory_manager,
    store_optimized_memory,
    build_optimized_context,
    check_and_summarize_session
)
from memory.chat_database import save_chat_to_db
from memory.user_profile import get_user_name as get_profile_name, set_user_name
from utils.kuro_prompt import build_kuro_prompt, sanitize_response
from utils.safety import validate_response, get_fallback_response
from utils.groq_client import GroqClient

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class OptimizedChatManager:
    """
    Optimized chat manager for Groq LLaMA 3 70B with 8K context limit
    
    Key optimizations:
    - Token-aware context building
    - Efficient memory retrieval (top 3 only)
    - Session summarization
    - Minimal RAM usage
    """
    
    def __init__(self):
        """Initialize the optimized chat manager"""
        try:
            # Initialize Groq client
            self.groq_client = GroqClient()
            logger.info("✅ Optimized chat manager initialized with Groq LLaMA 3 70B")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Groq model: {str(e)}")
            raise RuntimeError(f"AI model initialization failed: {str(e)}")
    
    def extract_name(self, text: str) -> Optional[str]:
        """
        Extract user name from text using pattern matching
        
        Args:
            text (str): Input text to analyze
            
        Returns:
            Optional[str]: Extracted name or None if not found
        """
        # Common patterns for name introduction
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
                logger.info(f"✅ Extracted name: {name}")
                return name
        
        return None
    
    def get_user_name(self, user_id: str) -> Optional[str]:
        """
        Retrieve stored user name from MongoDB user profile
        
        Args:
            user_id (str): User identifier
            
        Returns:
            Optional[str]: User's name if found
        """
        try:
            return get_profile_name(user_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to get user name: {e}")
            return None
    
    def store_user_name(self, user_id: str, name: str, context_message: str):
        """
        Store user name in both MongoDB profile and Pinecone memory
        
        Args:
            user_id (str): User identifier
            name (str): User's name
            context_message (str): Message context where name was mentioned
        """
        try:
            # Store in MongoDB profile
            set_user_name(user_id, name)
            
            # Store in Pinecone memory for context
            memory_text = f"User's name is {name}. Context: {context_message}"
            store_optimized_memory(
                text=memory_text,
                user_id=user_id,
                memory_type="profile",
                importance=0.9
            )
            
            logger.info(f"✅ Stored user name: {name} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store user name: {e}")
    
    def generate_optimized_response(
        self, 
        user_message: str, 
        context: str,
        token_usage: Dict[str, int],
        max_retries: int = 2
    ) -> str:
        """
        Generate AI response with token-aware context and retry logic
        
        Args:
            user_message (str): User's message
            context (str): Optimized context string
            token_usage (Dict[str, int]): Token usage breakdown
            max_retries (int): Maximum retry attempts
            
        Returns:
            str: AI response
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Build Kuro system prompt
                system_prompt = build_kuro_prompt()
                
                # Combine context and user message
                if context:
                    full_prompt = f"{context}\n\nUser: {user_message}\nAssistant:"
                else:
                    full_prompt = f"User: {user_message}\nAssistant:"
                
                # Log token usage
                logger.info(f"🔢 Token usage: {token_usage} (Total: {token_usage['total']})")
                
                # Generate response with Groq
                response = self.groq_client.generate_content(
                    prompt=full_prompt,
                    system_instruction=system_prompt
                )
                
                if not response:
                    logger.warning("⚠️ Empty response from Groq")
                    return get_fallback_response(user_message)
                
                # Sanitize response
                sanitized_response = sanitize_response(response)
                
                # Validate response safety
                is_valid, assessment = validate_response(sanitized_response, context)
                
                if is_valid:
                    logger.info(f"✅ Generated safe response (quality: {assessment.get('quality_score', 0):.2f})")
                    return sanitized_response
                else:
                    logger.warning(f"⚠️ Unsafe response detected: {assessment.get('blocked_reasons', [])}")
                    
                    # If this is the last retry, return fallback
                    if retry_count >= max_retries:
                        logger.info("Max retries reached, using fallback response")
                        return get_fallback_response(user_message)
                    
                    retry_count += 1
                    logger.info(f"Retrying generation (attempt {retry_count + 1})")
                    continue
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error generating AI response (attempt {retry_count + 1}): {error_msg}")
                
                # Handle Groq API rate limits
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    logger.warning("⚠️ Groq API rate limit exceeded")
                    return """🚧 **Development Mode Notice** 🚧

Hi! I'm currently in development and using the Groq API for LLaMA 3 70B. 

**We've hit the rate limit!** ⏰

This is temporary while we're building and testing. Please try again in a few moments.

For now, you can still:
- Browse your previous conversations
- Create new chat sessions (they'll be saved for when I'm back)
- Explore the interface

Thanks for your patience as we work on making this better! 🙏"""
                
                if retry_count >= max_retries:
                    return get_fallback_response(user_message)
                
                retry_count += 1
                continue
        
        # Fallback if all retries failed
        return get_fallback_response(user_message)
    
    def store_conversation_memory(
        self, 
        user_id: str, 
        user_message: str, 
        ai_response: str,
        session_id: Optional[str] = None
    ):
        """
        Store conversation in optimized memory format
        
        Args:
            user_id (str): User identifier
            user_message (str): User's message
            ai_response (str): AI's response
            session_id (Optional[str]): Session identifier
        """
        try:
            # Create compact conversation memory
            conversation_text = f"Q: {user_message}\nA: {ai_response[:300]}"  # Limit AI response length
            
            # Store with moderate importance
            store_optimized_memory(
                text=conversation_text,
                user_id=user_id,
                memory_type="conversation",
                importance=0.6,
                session_id=session_id
            )
            
            logger.info(f"✅ Stored conversation memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store conversation memory: {e}")
    
    def chat_with_optimized_memory(
        self, 
        user_id: str, 
        message: str, 
        session_id: Optional[str] = None
    ) -> str:
        """
        Process chat message with optimized memory system
        
        Args:
            user_id (str): User identifier
            message (str): User's message
            session_id (Optional[str]): Session identifier
            
        Returns:
            str: AI response
        """
        try:
            logger.info(f"🚀 Processing optimized chat for user {user_id}")
            
            # 1. Get user name (from profile)
            user_name = self.get_user_name(user_id) or "there"
            
            # 2. Handle name introduction in chat
            extracted_name = self.extract_name(message)
            if extracted_name and not self.get_user_name(user_id):
                self.store_user_name(user_id, extracted_name, message)
                user_name = extracted_name
                
                response = f"Nice to meet you, {user_name}! How can I help you today?"
                
                # Store the introduction exchange
                self.store_conversation_memory(user_id, message, response, session_id)
                save_chat_to_db(user_id, message, response, session_id)
                
                return response
            
            # 3. Check if session needs summarization (before processing)
            if session_id:
                summary = check_and_summarize_session(session_id, user_id)
                if summary:
                    logger.info(f"📋 Created session summary: {summary[:100]}...")
            
            # 4. Build optimized context (token-limited)
            context, token_usage = build_optimized_context(
                user_message=message,
                user_id=user_id,
                session_id=session_id,
                user_name=user_name if user_name != "there" else None
            )
            
            # 5. Generate response with optimized context
            response = self.generate_optimized_response(
                user_message=message,
                context=context,
                token_usage=token_usage
            )
            
            # 6. Store conversation in memory and database
            self.store_conversation_memory(user_id, message, response, session_id)
            save_chat_to_db(user_id, message, response, session_id)
            
            logger.info(f"✅ Optimized chat response generated for {user_name} (user_id: {user_id})")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in optimized chat: {str(e)}")
            return get_fallback_response(message)


# Global optimized chat manager instance
optimized_chat_manager = OptimizedChatManager()


def chat_with_optimized_memory(
    user_id: str, 
    message: str, 
    session_id: Optional[str] = None
) -> str:
    """
    Main function for optimized chat processing
    
    Args:
        user_id (str): User identifier
        message (str): User's message
        session_id (Optional[str]): Session identifier
        
    Returns:
        str: AI response
    """
    return optimized_chat_manager.chat_with_optimized_memory(
        user_id=user_id,
        message=message,
        session_id=session_id
    )


# Backward compatibility function
def chat_with_memory(
    user_id: str, 
    message: str, 
    session_id: Optional[str] = None
) -> str:
    """
    Backward compatibility wrapper for optimized chat
    """
    return chat_with_optimized_memory(user_id, message, session_id)
