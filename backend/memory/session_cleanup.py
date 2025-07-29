"""
Session Cleanup Module

This module handles the summarization and cleanup of chat sessions
to optimize memory usage while preserving important information.

Features:
- Session summarization using AI
- Memory cleanup and optimization
- Batch processing capabilities
- Error handling and logging
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from memory.memory_manager import store_memory, delete_session_memories
from memory.chat_database import get_chat_history_for_session
from utils.groq_client import GroqClient

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SessionCleanupManager:
    """
    Manager for session cleanup and summarization operations
    
    This class handles the process of summarizing chat sessions
    and cleaning up detailed memory to optimize storage.
    """
    
    def __init__(self):
        """Initialize the session cleanup manager"""
        try:
            self.groq_client = GroqClient()
            logger.info("✅ Session cleanup manager initialized with Groq")
        except Exception as e:
            logger.error(f"❌ Failed to initialize cleanup manager: {str(e)}")
            raise RuntimeError(f"Cleanup manager initialization failed: {str(e)}")
    
    def generate_session_summary(self, chat_history: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of a chat session using AI
        
        Args:
            chat_history (List[Dict]): List of chat messages
            
        Returns:
            str: Generated summary
        """
        try:
            if not chat_history:
                return "Empty session - no messages to summarize."
            
            # Format chat history for summarization
            chat_text = self._format_chat_for_summary(chat_history)
            
            # Create summarization prompt
            prompt = self._build_summary_prompt(chat_text)
            
            # Generate summary using Groq
            response = self.groq_client.generate_content(prompt)
            
            if response:
                summary = response.strip()
                logger.info("Session summary generated successfully")
                return summary
            else:
                logger.warning("Empty summary generated")
                return "Unable to generate summary for this session."
                
        except Exception as e:
            logger.error(f"Error generating session summary: {str(e)}")
            return f"Summary generation failed: {str(e)}"
    
    def _format_chat_for_summary(self, chat_history: List[Dict[str, Any]]) -> str:
        """
        Format chat history for summarization
        
        Args:
            chat_history (List[Dict]): Chat messages
            
        Returns:
            str: Formatted chat text
        """
        formatted_messages = []
        
        for msg in chat_history:
            user_msg = msg.get("message", "")
            assistant_msg = msg.get("reply", "")
            timestamp = msg.get("timestamp", "")
            
            if user_msg and assistant_msg:
                formatted_messages.append(f"User: {user_msg}")
                formatted_messages.append(f"Assistant: {assistant_msg}")
                formatted_messages.append("---")
        
        return "\n".join(formatted_messages)
    
    def _build_summary_prompt(self, chat_text: str) -> str:
        """
        Build a prompt for session summarization
        
        Args:
            chat_text (str): Formatted chat text
            
        Returns:
            str: Summarization prompt
        """
        prompt = f"""Please create a comprehensive summary of this conversation between a user and an AI assistant.

Focus on:
1. Key topics discussed
2. Important information shared by the user
3. Problems solved or advice given
4. User preferences or interests mentioned
5. Any personal details that should be remembered

Keep the summary concise but informative, highlighting the most important aspects of the conversation.

Conversation:
{chat_text}

Summary:"""
        
        return prompt
    
    async def summarize_and_cleanup_session(
        self, 
        session_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Summarize a session and clean up detailed memories
        
        Args:
            session_id (str): Session identifier
            user_id (str): User identifier
            
        Returns:
            Dict: Operation result
        """
        try:
            logger.info(f"Starting cleanup for session {session_id}")
            
            # 1. Get chat history from database
            chat_history = get_chat_history_for_session(session_id)
            
            if not chat_history:
                return {
                    "status": "error",
                    "message": "No chat history found for this session"
                }
            
            # 2. Generate summary
            summary = self.generate_session_summary(chat_history)
            
            # 3. Store summary in memory
            summary_metadata = {
                "user": user_id,
                "type": "session_summary",
                "session_id": session_id,
                "source": "session_cleanup",
                "original_message_count": len(chat_history),
                "cleanup_date": datetime.utcnow().isoformat()
            }
            
            memory_id = store_memory(summary, summary_metadata)
            
            # 4. Delete detailed session memories from Pinecone
            cleanup_success = delete_session_memories(session_id)
            
            # 5. Log the operation
            logger.info(f"Session {session_id} summarized and cleaned up successfully")
            
            return {
                "status": "success",
                "message": "Session summarized and cleaned up successfully",
                "summary_id": memory_id,
                "original_messages": len(chat_history),
                "cleanup_successful": cleanup_success
            }
            
        except Exception as e:
            logger.error(f"Error in session cleanup: {str(e)}")
            return {
                "status": "error",
                "message": f"Session cleanup failed: {str(e)}"
            }
    
    async def cleanup_old_sessions(
        self, 
        user_id: str, 
        days_old: int = 30,
        max_sessions: int = 10
    ) -> Dict[str, Any]:
        """
        Clean up old sessions for a user
        
        Args:
            user_id (str): User identifier
            days_old (int): Age threshold in days
            max_sessions (int): Maximum number of sessions to process
            
        Returns:
            Dict: Cleanup results
        """
        try:
            from backend.memory.chat_database import get_sessions_by_user
            
            # Get user sessions
            sessions = get_sessions_by_user(user_id)
            
            if not sessions:
                return {
                    "status": "success",
                    "message": "No sessions found for cleanup",
                    "processed": 0
                }
            
            # Filter old sessions
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_sessions = [
                s for s in sessions 
                if s.get("created_at", datetime.utcnow()) < cutoff_date
            ]
            
            # Limit the number of sessions to process
            sessions_to_process = old_sessions[:max_sessions]
            
            processed_count = 0
            errors = []
            
            # Process each session
            for session in sessions_to_process:
                try:
                    result = await self.summarize_and_cleanup_session(
                        session["session_id"], 
                        user_id
                    )
                    
                    if result["status"] == "success":
                        processed_count += 1
                    else:
                        errors.append(f"Session {session['session_id']}: {result['message']}")
                        
                except Exception as e:
                    errors.append(f"Session {session['session_id']}: {str(e)}")
            
            return {
                "status": "success",
                "message": f"Processed {processed_count} sessions",
                "processed": processed_count,
                "total_old_sessions": len(old_sessions),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in batch cleanup: {str(e)}")
            return {
                "status": "error",
                "message": f"Batch cleanup failed: {str(e)}"
            }

# Create global cleanup manager instance
cleanup_manager = SessionCleanupManager()

# Export function for backward compatibility
async def summarize_and_cleanup_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """Summarize and cleanup session using the global manager"""
    return await cleanup_manager.summarize_and_cleanup_session(session_id, user_id)

async def cleanup_old_sessions_for_user(
    user_id: str, 
    days_old: int = 30,
    max_sessions: int = 10
) -> Dict[str, Any]:
    """Cleanup old sessions using the global manager"""
    return await cleanup_manager.cleanup_old_sessions(user_id, days_old, max_sessions)

if __name__ == "__main__":
    # Test the cleanup functionality
    import asyncio
    
    async def test_cleanup():
        try:
            # Test session cleanup
            result = await summarize_and_cleanup_session("test_session", "test_user")
            print(f"✅ Cleanup test result: {result}")
            
        except Exception as e:
            print(f"❌ Cleanup test failed: {str(e)}")
    
    asyncio.run(test_cleanup())