"""
Chat Management Module

This module handles the core chat functionality, including AI responses,
user name extraction, memory integration, and conversation flow management.

Features:
- AI chat responses using Groq LLaMA 3 70B
- User name detection and storage
- Memory-aware conversations
- Chat history persistence
- Context-aware responses

Version: 2025-07-29 - Migrated from Gemini to Groq LLaMA 3 70B
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from memory.ultra_lightweight_memory import store_memory, get_relevant_memories_detailed, ultra_lightweight_memory_manager as memory_manager
from memory.chat_database import save_chat_to_db
from memory.user_profile import get_user_name as get_profile_name, set_user_name
from utils.kuro_prompt import build_kuro_prompt, sanitize_response
from utils.safety import validate_response, get_fallback_response
from utils.groq_client import GroqClient

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class ChatManager:
    """
    Chat management class for handling AI conversations
    
    This class manages the conversation flow, memory integration,
    and AI response generation for the chatbot.
    """
    
    def __init__(self):
        """Initialize the chat manager with Groq AI model"""
        try:
            # Initialize Groq client
            self.groq_client = GroqClient()
            logger.info("✅ Groq LLaMA 3 70B model initialized successfully")
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
                logger.info(f"Extracted name: {name}")
                return name
        
        return None
    
    def get_user_name(self, user_id: str) -> Optional[str]:
        """
        Retrieve stored user name from MongoDB user profile, fallback to memory if not found
        """
        try:
            # 1. Try MongoDB user profile
            name = get_profile_name(user_id)
            if name:
                return name
            # 2. Fallback to memory search
            memories = get_relevant_memories_detailed(
                query="name introduction", 
                user_filter=user_id, 
                top_k=5
            )
            for memory in memories:
                name = self.extract_name(memory["text"])
                if name:
                    return name
            return None
        except Exception as e:
            logger.error(f"Error retrieving user name: {str(e)}")
            return None
    
    def store_user_name(self, user_id: str, name: str, source_message: str):
        """
        Store user name in MongoDB user profile and memory
        """
        try:
            set_user_name(user_id, name)
            memory_text = f"My name is {name}"
            metadata = {
                "user": user_id,
                "type": "user_profile",
                "field": "name",
                "value": name,
                "source": "chat_introduction",
                "original_message": source_message
            }
            store_memory(memory_text, metadata, importance=0.9)  # High importance for name
            logger.info(f"Stored name '{name}' for user {user_id} (profile + memory)")
        except Exception as e:
            logger.error(f"Failed to store user name: {str(e)}")
    
    def generate_ai_response(self, user_message: str, context: Optional[str] = None, max_retries: int = 2) -> str:
        """
        Generate AI response using Kuro prompt system with safety validation
        
        Args:
            user_message (str): User's message
            context (Optional[str]): Context from memory/history
            max_retries (int): Maximum retry attempts for unsafe responses
            
        Returns:
            str: Safe, validated AI response
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Build Kuro prompt with system instruction
                prompt_package = build_kuro_prompt(user_message, context)
                
                # Generate response using Groq
                response = self.groq_client.generate_content(
                    prompt=prompt_package["user_prompt"],
                    system_instruction=prompt_package["system_instruction"]
                )
                
                if not response:
                    logger.warning("Empty response from Groq")
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
                    
                    # Add retry enhancement to context
                    from utils.safety import kuro_safety_validator
                    retry_enhancement = kuro_safety_validator.get_retry_prompt_enhancement(assessment)
                    enhanced_context = (context or "") + retry_enhancement
                    context = enhanced_context
                    
                    retry_count += 1
                    logger.info(f"Retrying generation (attempt {retry_count + 1})")
                    continue
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error generating AI response (attempt {retry_count + 1}): {error_msg}")
                
                # Handle Groq API rate limits
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    logger.warning("⚠️ Groq API rate limit exceeded - returning development message")
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
    
    def build_context_prompt(
        self, 
        user_name: str, 
        message: str, 
        relevant_memories: List[Dict[str, Any]],
        session_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build a context-aware prompt for the AI with smart memory organization
        
        Args:
            user_name (str): User's name
            message (str): Current user message
            relevant_memories (List[Dict]): Relevant past memories with metadata
            session_history (Optional[List[Dict]]): Recent messages from current session
            
        Returns:
            str: Formatted prompt for the AI
        """
        # Organize memories by category and importance
        organized_context = []
        
        # Add recent session context if available
        if session_history:
            recent_exchanges = session_history[-3:]  # Last 3 messages
            session_context = []
            for msg in recent_exchanges:
                session_context.extend([
                    f"User: {msg['user']}",
                    f"Assistant: {msg['assistant']}"
                ])
            organized_context.append(
                "🔄 Recent conversation:\n" + "\n".join(session_context)
            )
        
        # Add relevant memories organized by category
        if relevant_memories:
            memory_categories = {
                "user_profile": [],
                "preferences": [],
                "goals": [],
                "skills": [],
                "key_information": [],
                "conversation": []
            }
            
            # Sort memories by importance and category
            for memory in relevant_memories:
                category = memory.get("category", "general")
                if category in memory_categories:
                    memory_categories[category].append(memory["text"])
                else:
                    memory_categories["conversation"].append(memory["text"])
            
            # Add organized memories to context
            if memory_categories["user_profile"]:
                organized_context.append(
                    "👤 User Profile:\n" + "\n".join(memory_categories["user_profile"])
                )
            
            if memory_categories["preferences"]:
                organized_context.append(
                    "❤️ User Preferences:\n" + "\n".join(memory_categories["preferences"])
                )
                
            if memory_categories["goals"]:
                organized_context.append(
                    "🎯 User Goals:\n" + "\n".join(memory_categories["goals"])
                )
                
            if memory_categories["skills"]:
                organized_context.append(
                    "�️ User Skills:\n" + "\n".join(memory_categories["skills"])
                )
            
            if memory_categories["key_information"]:
                organized_context.append(
                    "🔑 Key Information:\n" + "\n".join(memory_categories["key_information"])
                )
            
            if memory_categories["conversation"]:
                organized_context.append(
                    "💭 Related Past Conversations:\n" + "\n".join(memory_categories["conversation"])
                )
        
        context_str = "\n\n".join(organized_context) if organized_context else "No previous context available."
        
        prompt = f"""You are a helpful and friendly AI assistant talking to {user_name}.
You have access to previous conversations and context to provide personalized responses.

{context_str}

Current message:
👤 {user_name}: {message}

Instructions for responding:
1. ALWAYS reference recent conversation context - if we were discussing a topic, continue that conversation naturally
2. Use stored memories about {user_name}'s interests, preferences, and past requests to be more helpful
3. Be conversational and engaging, not repetitive
4. If {user_name} says something like "both of them" or "that one", refer to the recent context to understand what they mean
5. Don't ask the same questions repeatedly - build on what you already know
6. Give specific, actionable advice when asked for recommendations
7. Remember that continuing a conversation is better than starting over

🤖 Assistant:"""
        
        return prompt
    
    def chat_with_memory(
        self, 
        user_id: str, 
        message: str, 
        session_id: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """
        Process a chat message with memory integration
        
        Args:
            user_id (str): User identifier
            message (str): User's message
            session_id (Optional[str]): Session identifier
            top_k (int): Number of memories to retrieve
            
        Returns:
            str: AI response
        """
        try:
            # 1. Get user name (popup handles name collection, so we don't ask)
            user_name = self.get_user_name(user_id) or "there"  # Fallback to generic greeting
            
            # 2. Handle name introduction in chat (if user mentions name while chatting)
            extracted_name = self.extract_name(message)
            if extracted_name and not self.get_user_name(user_id):
                self.store_user_name(user_id, extracted_name, message)
                user_name = extracted_name
                
                response = f"Nice to meet you, {user_name}! How can I help you?"
                
                # Store the introduction exchange
                self._store_chat_memory(user_id, message, response, session_id)
                save_chat_to_db(user_id, message, response, session_id)
                
                return response
            
            # 3. Retrieve relevant memories for context (optimized)
            relevant_memories = []
            try:
                relevant_memories = get_relevant_memories_detailed(
                    query=message, 
                    user_filter=user_id, 
                    top_k=3  # Reduced from default 5 for faster responses
                )
                logger.info(f"Retrieved {len(relevant_memories)} relevant memories for user {user_id}")
            except Exception as e:
                logger.warning(f"Memory retrieval failed: {str(e)}")
                relevant_memories = []
            
            # 4. Get recent session history for context
            session_history = None
            if session_id:
                try:
                    from memory.chat_database import get_chat_by_session
                    chat_data = get_chat_by_session(session_id)
                    if chat_data and len(chat_data) > 1:  # More than just current message
                        session_history = chat_data[-6:]  # Last 6 messages for context
                except Exception as e:
                    logger.warning(f"Failed to get session history: {str(e)}")
            
            # 5. Build concise context from memories and history
            context_parts = []
            
            # Add recent session context (more natural)
            if session_history:
                recent_exchanges = session_history[-2:]  # Reduced to last 2 messages
                session_context = []
                for msg in recent_exchanges:
                    session_context.append(f"Previous: {msg['user']} → {msg['assistant']}")
                context_parts.append("Recent context: " + " | ".join(session_context))
            
            # Add relevant memories (more concise)
            if relevant_memories:
                memory_snippets = []
                for memory in relevant_memories[:3]:  # Limit to top 3 memories
                    # Extract key information from memory
                    text = memory["text"][:100]  # Limit length
                    memory_snippets.append(text)
                context_parts.append("Past context: " + " | ".join(memory_snippets))
            
            # Only add user name if it's relevant to the conversation
            if user_name and (
                "name" in message.lower() or 
                any(greeting in message.lower() for greeting in ["hello", "hi", "hey"]) or
                not session_history  # First message in session
            ):
                context_parts.append(f"User: {user_name}")
            
            context = " | ".join(context_parts) if context_parts else None
            
            # 6. Generate response using Kuro system
            response = self.generate_ai_response(message, context)
            
            # 7. Store the conversation in memory and database
            self._store_chat_memory(user_id, message, response, session_id)
            save_chat_to_db(user_id, message, response, session_id)
            
            logger.info(f"Chat response generated for {user_name} (user_id: {user_id})")
            return response
            
        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}")
            return "I apologize, but I encountered an error while processing your message. Please try again."
    
    def _store_chat_memory(
        self, 
        user_id: str, 
        message: str, 
        response: str, 
        session_id: Optional[str] = None
    ):
        """
        Store chat exchange in memory for future context with intelligent importance
        
        Args:
            user_id (str): User identifier
            message (str): User's message
            response (str): AI's response
            session_id (Optional[str]): Session identifier
        """
        try:
            # Only store important exchanges to reduce noise
            message_lower = message.lower()
            
            # Skip storing very short or common messages
            if len(message) < 10 or any(skip in message_lower for skip in ["ok", "thanks", "yes", "no"]):
                return
            
            # Store concise exchange format
            chat_text = f"Q: {message}\nA: {response[:200]}"  # Limit response length in memory
            metadata = {
                "user": user_id,
                "type": "chat_exchange",
                "source": "chat_manager",
                "session_id": session_id or "default"
            }
            
            # Calculate importance based on message content
            importance = 0.3  # Base importance for regular chat
            
            # Higher importance for requests, preferences, and key information
            if any(keyword in message_lower for keyword in ["i love", "i like", "i prefer", "favorite", "interested in", "i enjoy", "hobby"]):
                importance = 0.8  # High importance for preferences
            elif any(keyword in message_lower for keyword in ["i need", "suggest", "recommend", "help me", "looking for", "can you"]):
                importance = 0.7  # High importance for requests
            elif any(keyword in message_lower for keyword in ["important", "remember", "key", "note"]):
                importance = 0.9  # Very high importance for explicit requests to remember
            
            store_memory(chat_text, metadata, importance=importance)
            
        except Exception as e:
            logger.error(f"Failed to store chat memory: {str(e)}")
            # Don't raise exception here to avoid breaking the chat flow

# Create global chat manager instance
chat_manager = ChatManager()

# Export function for backward compatibility
def chat_with_memory(
    user_id: str, 
    message: str, 
    session_id: Optional[str] = None,
    top_k: int = 5
) -> str:
    """Process chat message using the global chat manager"""
    return chat_manager.chat_with_memory(user_id, message, session_id, top_k)

if __name__ == "__main__":
    # Test the chat manager
    try:
        # Test name extraction
        test_message = "Hi, my name is Alice and I love programming"
        name = chat_manager.extract_name(test_message)
        print(f"✅ Extracted name: {name}")
        
        # Test chat functionality
        response = chat_with_memory("test_user", "Hello, I'm Bob")
        print(f"✅ Chat response: {response}")
        
    except Exception as e:
        print(f"❌ Chat manager test failed: {str(e)}")