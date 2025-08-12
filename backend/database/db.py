"""
Database Connection Module

This module handles the MongoDB connection for the AI chatbot application.
It provides a centralized database client that can be imported and used
throughout the application.

Features:
- MongoDB connection with error handling
- Environment variable configuration
- Connection testing and validation
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
MONGO_URI = os.getenv("MONGODB_URI", os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot_db"))
DATABASE_NAME = "chatbot_db"

class DatabaseConnection:
    """
    MongoDB database connection manager
    
    This class provides a singleton pattern for database connections
    and includes connection validation and error handling.
    """
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Do not connect on import; connect lazily on first use
        pass
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            self._client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,         # 10 second connection timeout
                socketTimeoutMS=20000,          # 20 second socket timeout
            )
            
            # Test the connection
            self._client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            # Defer raising to actual DB usage to avoid startup crash
            raise ConnectionError(f"Database connection failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ Unexpected database error: {str(e)}")
            raise
    
    @property
    def client(self):
        """Get the MongoDB client"""
        if self._client is None:
            self._connect()
        return self._client
    
    @property
    def database(self):
        """Get the main database"""
        return self.client[DATABASE_NAME]
    
    def test_connection(self):
        """Test if the database connection is working"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    def close_connection(self):
        """Close the database connection"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Database connection closed")

_db_singleton: DatabaseConnection | None = None

def get_db_connection() -> DatabaseConnection:
    global _db_singleton
    if _db_singleton is None:
        _db_singleton = DatabaseConnection()
    return _db_singleton

def get_client():
    return get_db_connection().client

def get_database():
    return get_db_connection().database

class LazyCollection:
    """Proxy that fetches the real collection on first attribute access."""
    def __init__(self, name: str):
        self._name = name
    def _col(self):
        return get_database()[self._name]
    def __getattr__(self, item):
        return getattr(self._col(), item)
    def __repr__(self):
        return f"<LazyCollection name={self._name}>"

# Lazy collection proxies to avoid connecting at import time
chat_collection = LazyCollection("chat_sessions")
session_titles_collection = LazyCollection("session_titles")
users_collection = LazyCollection("users")
conversation_summaries_collection = LazyCollection("conversation_summaries")

class LazyDatabase:
    """Proxy to the actual Database object (for backward-compatible import)."""
    def __getattr__(self, item):
        return getattr(get_database(), item)
    def __getitem__(self, key):
        return get_database()[key]
    def __repr__(self):
        return "<LazyDatabase proxy>"

class LazyClient:
    """Proxy to the actual MongoClient (for backward-compatible import)."""
    def __getattr__(self, item):
        return getattr(get_client(), item)
    def __repr__(self):
        return "<LazyClient proxy>"

# Backward-compatible exports
database = LazyDatabase()
client = LazyClient()

def get_database_legacy():
    """Legacy alias; prefer get_database()."""
    return get_database()

def get_collection(collection_name: str):
    """
    Get a specific collection
    
    Args:
        collection_name (str): Name of the collection
        
    Returns:
        Collection: MongoDB collection instance
    """
    return get_database()[collection_name]

def check_database_health():
    """
    Check database health and return status
    
    Returns:
        dict: Health status information
    """
    try:
        # Test connection
        get_client().admin.command('ping')

        # Get database stats
        stats = get_database().command("dbstats")

        return {
            "status": "healthy",
            "connected": True,
            "database": DATABASE_NAME,
            "collections": len(get_database().list_collection_names()),
            "size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }

# Initialize database collections with indexes for better performance
def initialize_database():
    """
    Initialize database with required indexes and collections
    
    This function should be called once during application startup
    to ensure optimal database performance.
    """
    try:
        # Create indexes for better query performance
        
        # Chat sessions indexes
        chat_collection.create_index([("user_id", 1), ("session_id", 1)])
        chat_collection.create_index([("session_id", 1), ("timestamp", 1)])
        chat_collection.create_index([("user_id", 1), ("timestamp", -1)])
        
        # Session titles indexes
        session_titles_collection.create_index([("user_id", 1), ("created_at", -1)])
        session_titles_collection.create_index([("session_id", 1)], unique=True)
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        raise

if __name__ == "__main__":
    # Test the database connection
    health = check_database_health()
    print(f"Database Health: {health}")
    
    if health["status"] == "healthy":
        initialize_database()
        print("Database initialized successfully!")