"""
Chat Database Module

This module handles all database operations related to chat sessions,
message storage, and session management using MongoDB.

Features:
- Chat message persistence
- Session management
- User session retrieval
- Session title management
- Chat history queries
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from backend.database.db import (
    chat_collection, 
    session_titles_collection,
    database
)

# Configure logging
logger = logging.getLogger(__name__)

class ChatDatabase:
    def __init__(self):
        self.chat_collection = chat_collection
        self.session_titles = session_titles_collection
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Ensure all necessary indexes exist for optimal performance"""
        try:
            # Indexes for chat collection
            self.chat_collection.create_index([("session_id", 1), ("timestamp", 1)])
            self.chat_collection.create_index([("user_id", 1), ("timestamp", -1)])
            self.chat_collection.create_index([
                ("session_id", 1), 
                ("metadata.sequence_number", 1)
            ])
            
            # Indexes for session titles
            self.session_titles.create_index([("user_id", 1), ("created_at", -1)])
            self.session_titles.create_index("session_id", unique=True)
            
            logger.info("Database indexes verified")
        except Exception as e:
            logger.error(f"Error ensuring indexes: {str(e)}")

    def _get_next_sequence_number(self, session_id: str) -> int:
        """Get the next sequence number for messages in a session"""
        try:
            last_message = self.chat_collection.find_one(
                {"session_id": session_id},
                sort=[("metadata.sequence_number", -1)]
            )
            return (last_message.get("metadata", {}).get("sequence_number", 0) + 1) if last_message else 1
        except Exception as e:
            logger.error(f"Error getting sequence number: {str(e)}")
            return 1

    def _update_session_metadata(self, session_id: str, user_id: str, message: str):
        """Update session metadata including title and activity timestamps"""
        try:
            update_data = {
                "last_activity": datetime.utcnow(),
                "message_count": self.chat_collection.count_documents({"session_id": session_id})
            }
            
            # Update or create session title
            existing_title = self.session_titles.find_one({"session_id": session_id})
            if not existing_title:
                title_document = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "title": message[:100],
                    "created_at": datetime.utcnow(),
                    **update_data
                }
                self.session_titles.insert_one(title_document)
            else:
                self.session_titles.update_one(
                    {"session_id": session_id},
                    {"$set": update_data}
                )
        except Exception as e:
            logger.error(f"Error updating session metadata: {str(e)}")

    def save_chat_to_db(self, user_id: str, message: str, reply: str, session_id: Optional[str] = None) -> str:
        try:
            if not session_id:
                session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            # Prepare chat document with enhanced metadata
            chat_document = {
                "user_id": user_id,
                "session_id": session_id,
                "message": message,
                "reply": reply,
                "timestamp": datetime.utcnow(),
                "metadata": {
                    "message_length": len(message),
                    "reply_length": len(reply),
                    "type": "chat_message",
                    "sequence_number": self._get_next_sequence_number(session_id)
                }
            }
            
            # Insert with automatic expiry for old sessions
            result = self.chat_collection.insert_one(chat_document)
            
            # Update session metadata
            self._update_session_metadata(session_id, user_id, message)
            
            # Index management - ensure we have proper indexes
            self._ensure_indexes()
            
            logger.info(f"Chat saved: {result.inserted_id} for session {session_id}")
            return session_id
        except PyMongoError as e:
            logger.error(f"Database error saving chat: {str(e)}")
            raise RuntimeError(f"Failed to save chat: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving chat: {str(e)}")
            raise

    def _ensure_session_title(self, session_id: str, user_id: str, message: str):
        try:
            existing_title = self.session_titles.find_one({"session_id": session_id})
            if not existing_title:
                title_document = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "title": message[:100],
                    "created_at": datetime.utcnow()
                }
                self.session_titles.insert_one(title_document)
                logger.info(f"Session title created for {session_id}")
        except PyMongoError as e:
            logger.error(f"Error creating session title: {str(e)}")

    def create_new_session(self, user_id: str) -> str:
        try:
            session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            title_document = {
                "session_id": session_id,
                "user_id": user_id,
                "title": "New Chat",
                "created_at": datetime.utcnow()
            }
            self.session_titles.insert_one(title_document)
            logger.info(f"New session created for {user_id} with ID {session_id}")
            return session_id
        except PyMongoError as e:
            logger.error(f"Database error creating session: {str(e)}")
            raise

    def get_sessions_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            sessions = self.session_titles.find({"user_id": user_id}).sort("created_at", DESCENDING)
            return [{
                "session_id": s["session_id"],
                "title": s["title"],
                "created_at": s["created_at"]
            } for s in sessions]
        except PyMongoError as e:
            logger.error(f"Database error retrieving sessions: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving sessions: {str(e)}")
            return []

    def get_chat_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            chats = self.chat_collection.find({"session_id": session_id}).sort("timestamp", 1)
            return [{
                "user": c["message"],
                "assistant": c["reply"],
                "timestamp": c["timestamp"]
            } for c in chats]
        except PyMongoError as e:
            logger.error(f"Database error retrieving chat history: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving chat history: {str(e)}")
            return []

    def get_all_chats_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            chats = self.chat_collection.find({"user_id": user_id}).sort("timestamp", 1)
            return [{
                "session_id": c["session_id"],
                "user": c["message"],
                "assistant": c["reply"],
                "timestamp": c["timestamp"]
            } for c in chats]
        except PyMongoError as e:
            logger.error(f"Database error retrieving user history: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving user history: {str(e)}")
            return []

    def delete_session_by_id(self, session_id: str) -> bool:
        try:
            chat_result = self.chat_collection.delete_many({"session_id": session_id})
            title_result = self.session_titles.delete_one({"session_id": session_id})
            return chat_result.deleted_count > 0 or title_result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Database error deleting session: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting session: {str(e)}")
            return False

    def rename_session_title(self, session_id: str, new_title: str) -> bool:
        try:
            result = self.session_titles.update_one({"session_id": session_id}, {"$set": {"title": new_title[:100]}})
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Database error renaming session: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error renaming session: {str(e)}")
            return False

    def get_chat_history_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            messages = self.chat_collection.find({"session_id": session_id}).sort("timestamp", 1)
            return [{
                "session_id": m["session_id"],
                "user_id": m["user_id"],
                "message": m["message"],
                "reply": m["reply"],
                "timestamp": m["timestamp"]
            } for m in messages]
        except PyMongoError as e:
            logger.error(f"Database error retrieving session history: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error retrieving session history: {str(e)}")
            return []

    def get_database_stats(self) -> Dict[str, Any]:
        try:
            chat_count = self.chat_collection.count_documents({})
            session_count = self.session_titles.count_documents({})
            recent_chats = self.chat_collection.count_documents({
                "timestamp": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
            })
            return {
                "total_messages": chat_count,
                "total_sessions": session_count,
                "messages_today": recent_chats,
                "collections": {
                    "chat_sessions": chat_count,
                    "session_titles": session_count
                }
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}

chat_db = ChatDatabase()

def save_chat_to_db(user_id: str, message: str, reply: str, session_id: Optional[str] = None) -> str:
    return chat_db.save_chat_to_db(user_id, message, reply, session_id)

def get_sessions_by_user(user_id: str) -> List[Dict[str, Any]]:
    return chat_db.get_sessions_by_user(user_id)

def get_chat_by_session(session_id: str) -> List[Dict[str, Any]]:
    return chat_db.get_chat_by_session(session_id)

def get_all_chats_by_user(user_id: str) -> List[Dict[str, Any]]:
    return chat_db.get_all_chats_by_user(user_id)

def delete_session_by_id(session_id: str) -> bool:
    return chat_db.delete_session_by_id(session_id)

def rename_session_title(session_id: str, new_title: str) -> bool:
    return chat_db.rename_session_title(session_id, new_title)

def get_chat_history_for_session(session_id: str) -> List[Dict[str, Any]]:
    return chat_db.get_chat_history_for_session(session_id)

def create_new_session(user_id: str) -> str:
    return chat_db.create_new_session(user_id)

def get_database_stats() -> Dict[str, Any]:
    return chat_db.get_database_stats()
