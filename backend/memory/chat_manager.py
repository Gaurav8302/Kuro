"""
Chat Management Module

This module handles the core chat functionality, including AI responses,
user name extraction, memory integration, and conversation flow management.

Features:
- AI chat responses using Google Gemini
- User name detection and storage
- Memory-aware conversations
- Chat history persistence
- Context-aware responses
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

from memory.ultra_lightweight_memory import store_memory, get_relevant_memories_detailed, ultra_lightweight_memory_manager as memory_manager
from memory.chat_database import save_chat_to_db
from memory.user_profile import get_user_name as get_profile_name, set_user_name

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

genai.configure(api_key=GOOGLE_API_KEY)

class ChatManager:
    """
    Chat management class for handling AI conversations
    
    This class manages the conversation flow, memory integration,
    and AI response generation for the chatbot.
    """
    
    def __init__(self):
        """Initialize the chat manager with AI model"""
        try:
            self.gemini = genai.GenerativeModel("models/gemini-1.5-flash")
            logger.info("✅ Google Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini model: {str(e)}")
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
                top_k=5,
                memory_types=["user_profile"]
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
    
    def generate_ai_response(self, prompt: str) -> str:
        """
        Generate AI response using Google Gemini
        
        Args:
            prompt (str): Input prompt for the AI
            
        Returns:
            str: AI-generated response
        """
        try:
            response = self.gemini.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return "I apologize, but I'm having trouble generating a response right now. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I'm sorry, I encountered an error while processing your message. Please try again."
    
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
            # 1. Check for user name in current message
            extracted_name = self.extract_name(message)
            user_name = self.get_user_name(user_id)
            
            # 2. Handle name introduction
            if extracted_name and not user_name:
                self.store_user_name(user_id, extracted_name, message)
                user_name = extracted_name
                
                response = f"Nice to meet you, {user_name}! I'll remember your name for our future conversations. How can I help you today?"
                
                # Store the introduction exchange
                self._store_chat_memory(user_id, message, response, session_id)
                save_chat_to_db(user_id, message, response, session_id)
                
                return response
            
            # 3. Handle unknown user
            if not user_name:
                response = "Hello! I don't think we've been introduced yet. What's your name?"
                
                # Store the greeting exchange
                self._store_chat_memory(user_id, message, response, session_id)
                save_chat_to_db(user_id, message, response, session_id)
                
                return response
            
            # 4. Retrieve relevant memories for context with lower threshold
            relevant_memories = get_relevant_memories_detailed(
                query=message, 
                user_filter=user_id, 
                top_k=top_k
            )
            
            # 5. Get recent session history for context
            session_history = None
            if session_id:
                try:
                    from memory.chat_database import get_chat_by_session
                    chat_data = get_chat_by_session(session_id)
                    if chat_data and len(chat_data) > 1:  # More than just current message
                        session_history = chat_data[-6:]  # Last 6 messages for context
                except Exception as e:
                    logger.warning(f"Failed to get session history: {str(e)}")
            
            # 6. Generate context-aware response
            prompt = self.build_context_prompt(user_name, message, relevant_memories, session_history)
            response = self.generate_ai_response(prompt)
            
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
            # Store the full exchange
            chat_text = f"User: {message}\nAssistant: {response}"
            metadata = {
                "user": user_id,
                "type": "chat_exchange",
                "source": "chat_manager",
                "session_id": session_id or "default"
            }
            
            # Calculate importance based on message content
            importance = 0.3  # Base importance for regular chat
            
            # Higher importance for requests, preferences, and key information
            message_lower = message.lower()
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