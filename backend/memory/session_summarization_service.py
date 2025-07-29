"""
Periodic Session Summarization Service

This module provides background processing for:
1. Automatic session summarization after 10+ messages
2. Memory cleanup for old, low-importance memories
3. Performance monitoring and optimization

Version: 2025-07-30 - Optimized for Groq LLaMA 3 70B
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import time

from memory.optimized_memory_manager import get_optimized_memory_manager
from memory.chat_database import get_all_chats_by_user

# Configure logging
logger = logging.getLogger(__name__)


class SessionSummarizationService:
    """
    Background service for session summarization and memory optimization
    """
    
    def __init__(self):
        """Initialize the summarization service"""
        self.is_running = False
        self.summarization_thread = None
        self.check_interval = 300  # Check every 5 minutes
        self.processed_sessions = set()
        
        logger.info("✅ Session summarization service initialized")
    
    def start(self):
        """Start the background summarization service"""
        if self.is_running:
            logger.warning("⚠️ Summarization service is already running")
            return
        
        self.is_running = True
        self.summarization_thread = threading.Thread(
            target=self._run_background_processing,
            daemon=True
        )
        self.summarization_thread.start()
        
        logger.info("🚀 Session summarization service started")
    
    def stop(self):
        """Stop the background summarization service"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.summarization_thread:
            self.summarization_thread.join(timeout=5)
        
        logger.info("🛑 Session summarization service stopped")
    
    def _run_background_processing(self):
        """Main background processing loop"""
        while self.is_running:
            try:
                # Process session summarization
                self._process_session_summarization()
                
                # Process memory cleanup (less frequent)
                if int(time.time()) % (self.check_interval * 4) == 0:
                    self._process_memory_cleanup()
                
                # Sleep for check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in background processing: {e}")
                time.sleep(60)  # Wait longer if there's an error
    
    def _process_session_summarization(self):
        """Process sessions that need summarization"""
        try:
            # Get all users with recent activity (last 24 hours)
            # This is a simplified approach - in production, you'd want to
            # track active sessions more efficiently
            
            from memory.chat_database import get_sessions_by_user
            
            # Get recently active sessions
            cutoff_time = datetime.now() - timedelta(hours=24)
            cutoff_iso = cutoff_time.isoformat()
            
            # Query sessions with recent activity
            recent_sessions = []
            try:
                # This would need to be implemented based on your MongoDB schema
                # For now, we'll use a placeholder approach
                logger.info("🔍 Checking for sessions needing summarization...")
                
                # Check a sample of users (in production, you'd want a more efficient approach)
                sample_user_ids = ["user1", "user2", "user3"]  # Placeholder
                
                for user_id in sample_user_ids:
                    try:
                        sessions = get_sessions_by_user(user_id)
                        for session in sessions:
                            session_id = session.get("session_id")
                            if session_id and session_id not in self.processed_sessions:
                                manager = get_optimized_memory_manager()
                                if manager.should_summarize_session(session_id):
                                    self._summarize_session(session_id, user_id)
                                    self.processed_sessions.add(session_id)
                                    
                                    # Limit processing per cycle to avoid overload
                                    if len(recent_sessions) >= 5:
                                        break
                        
                        if len(recent_sessions) >= 5:
                            break
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Error processing user {user_id}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"❌ Error querying recent sessions: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error in session summarization processing: {e}")
    
    def _summarize_session(self, session_id: str, user_id: str):
        """Summarize a specific session"""
        try:
            logger.info(f"📝 Summarizing session {session_id} for user {user_id}")
            
            manager = get_optimized_memory_manager()
            summary = manager.summarize_session(session_id, user_id)
            
            if summary:
                logger.info(f"✅ Session {session_id} summarized: {summary[:100]}...")
            else:
                logger.warning(f"⚠️ Failed to summarize session {session_id}")
                
        except Exception as e:
            logger.error(f"❌ Error summarizing session {session_id}: {e}")
    
    def _process_memory_cleanup(self):
        """Process memory cleanup for old, low-importance memories"""
        try:
            logger.info("🧹 Starting memory cleanup process...")
            
            # Get list of users to clean up
            # This is a placeholder - in production, you'd want to track this more efficiently
            cleanup_users = ["user1", "user2", "user3"]  # Placeholder
            
            total_cleaned = 0
            for user_id in cleanup_users:
                try:
                    manager = get_optimized_memory_manager()
                    cleaned_count = manager.cleanup_old_memories(
                        user_id=user_id,
                        days_old=30
                    )
                    total_cleaned += cleaned_count
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error cleaning up memories for user {user_id}: {e}")
                    continue
            
            logger.info(f"✅ Memory cleanup completed: {total_cleaned} memories cleaned")
            
        except Exception as e:
            logger.error(f"❌ Error in memory cleanup processing: {e}")
    
    def summarize_session_on_demand(self, session_id: str, user_id: str) -> Optional[str]:
        """
        Summarize a session on demand (synchronous)
        
        Args:
            session_id (str): Session identifier
            user_id (str): User identifier
            
        Returns:
            Optional[str]: Summary if successful
        """
        try:
            manager = get_optimized_memory_manager()
            if manager.should_summarize_session(session_id):
                summary = manager.summarize_session(session_id, user_id)
                if summary:
                    self.processed_sessions.add(session_id)
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in on-demand summarization: {e}")
            return None
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the summarization service
        
        Returns:
            Dict[str, Any]: Service statistics
        """
        return {
            "is_running": self.is_running,
            "processed_sessions_count": len(self.processed_sessions),
            "check_interval_seconds": self.check_interval,
            "last_check": datetime.now().isoformat()
        }


# Global service instance
summarization_service = SessionSummarizationService()


def start_summarization_service():
    """Start the global summarization service"""
    summarization_service.start()


def stop_summarization_service():
    """Stop the global summarization service"""
    summarization_service.stop()


def summarize_session_now(session_id: str, user_id: str) -> Optional[str]:
    """Summarize a session immediately (on-demand)"""
    return summarization_service.summarize_session_on_demand(session_id, user_id)


def get_summarization_stats() -> Dict[str, Any]:
    """Get summarization service statistics"""
    return summarization_service.get_service_stats()


# Auto-start the service when module is imported (in production)
if os.getenv("ENVIRONMENT") == "production":
    logger.info("🚀 Auto-starting summarization service in production mode")
    start_summarization_service()
else:
    logger.info("💡 Summarization service available - call start_summarization_service() to begin")
