"""
User Profile Database Module

This module handles user profile storage and retrieval (e.g., name) in MongoDB.
"""

from backend.database.db import users_collection
import logging
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

def get_user_profile(user_id: str) -> dict | None:
    try:
        return users_collection.find_one({"user_id": user_id})
    except PyMongoError as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        return None

def set_user_name(user_id: str, name: str):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"name": name}},
            upsert=True
        )
        logger.info(f"Set name '{name}' for user {user_id}")
    except PyMongoError as e:
        logger.error(f"Error setting user name: {str(e)}")

def get_user_name(user_id: str) -> str | None:
    profile = get_user_profile(user_id)
    return profile["name"] if profile and "name" in profile else None
