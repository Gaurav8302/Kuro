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
        if self._client is None:
            self._connect()
    
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

# Create a global database connection instance
if os.getenv("DISABLE_MEMORY_INIT") == "1":
    # In-memory fallback for tests / local minimal runs
    import uuid
    class _InsertResult:
        def __init__(self, _id):
            self.inserted_id = _id
    def _get_nested(doc: dict, dotted: str):
        cur = doc
        for part in dotted.split('.'):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur
    class _Cursor:
        def __init__(self, docs):
            self._docs = list(docs)
        def sort(self, key, direction=None):
            items = self._docs
            if isinstance(key, list):
                keys = key
            else:
                keys = [(key, direction or 1)]
            # Apply sorts in reverse for stable multi-key
            for k, dirn in reversed(keys):
                rev = dirn == -1
                self._docs = sorted(self._docs, key=lambda d: _get_nested(d, k) if _get_nested(d, k) is not None else 0, reverse=rev)
            return self
        def limit(self, n: int):
            self._docs = self._docs[:n]
            return self
        def __iter__(self):
            return iter(self._docs)
    class InMemoryCollection:
        def __init__(self):
            self._docs = []
        def create_index(self, *args, **kwargs):
            return None
        def find_one(self, query=None, sort=None):
            query = query or {}
            matches = [d for d in self._docs if _match(d, query)]
            if sort:
                # sort can be list of tuples
                cur = _Cursor(matches).sort(sort)
                matches = list(cur)
            return matches[0] if matches else None
        def find(self, query=None):
            query = query or {}
            return _Cursor([d for d in self._docs if _match(d, query)])
        def insert_one(self, doc):
            if "_id" not in doc:
                doc["_id"] = uuid.uuid4().hex
            self._docs.append(dict(doc))
            return _InsertResult(doc["_id"])
        def delete_one(self, query):
            for i, d in enumerate(self._docs):
                if _match(d, query):
                    self._docs.pop(i)
                    return {"deleted_count": 1}
            return {"deleted_count": 0}
        def delete_many(self, query):
            to_keep = []
            deleted = 0
            for d in self._docs:
                if _match(d, query):
                    deleted += 1
                else:
                    to_keep.append(d)
            self._docs = to_keep
            return {"deleted_count": deleted}
        def update_one(self, query, update):
            for d in self._docs:
                if _match(d, query):
                    if "$set" in update:
                        d.update(update["$set"])
                    if "$inc" in update:
                        for k, v in update["$inc"].items():
                            d[k] = d.get(k, 0) + v
                    return {"matched_count": 1, "modified_count": 1}
            return {"matched_count": 0, "modified_count": 0}
        def count_documents(self, query):
            return len([d for d in self._docs if _match(d, query)])
    def _match(doc, query):
        # Supports equality, nested dotted keys, $or, regex, and basic comparison ops
        if not query:
            return True
        if "$or" in query:
            return any(_match(doc, q) for q in query["$or"])
        for k, v in query.items():
            if k == "$or":
                continue
            field_val = _get_nested(doc, k)
            if isinstance(v, dict):
                # Regex
                if "$regex" in v:
                    import re
                    pattern = v.get("$regex", "")
                    flags = re.I if v.get("$options") == "i" else 0
                    if not re.search(pattern, str(field_val or ""), flags):
                        return False
                # Comparisons
                if "$gt" in v and not (field_val is not None and field_val > v["$gt"]):
                    return False
                if "$gte" in v and not (field_val is not None and field_val >= v["$gte"]):
                    return False
                if "$lt" in v and not (field_val is not None and field_val < v["$lt"]):
                    return False
                if "$lte" in v and not (field_val is not None and field_val <= v["$lte"]):
                    return False
                if "$in" in v and field_val not in v["$in"]:
                    return False
                if "$nin" in v and field_val in v["$nin"]:
                    return False
            else:
                if field_val != v:
                    return False
        return True
    class InMemoryDatabase:
        def __init__(self, name: str):
            self._name = name
            self._cols = {}
        def __getitem__(self, name: str):
            if name not in self._cols:
                self._cols[name] = InMemoryCollection()
            return self._cols[name]
        def list_collection_names(self):
            return list(self._cols.keys())
        def command(self, name: str):
            if name == "dbstats":
                return {"dataSize": 0}
            return {}
    class _DummyClient:
        def __init__(self, dbname: str):
            self._db = InMemoryDatabase(dbname)
        def __getitem__(self, name: str):
            return InMemoryDatabase(name)
        @property
        def admin(self):
            class _A:
                def command(self, *a, **k):
                    return {"ok": 1}
            return _A()

    database = InMemoryDatabase(DATABASE_NAME)
    client = _DummyClient(DATABASE_NAME)
    chat_collection = database["chat_sessions"]
    session_titles_collection = database["session_titles"]
    users_collection = database["users"]
    conversation_summaries_collection = database["conversation_summaries"]
else:
    db_connection = DatabaseConnection()
    # Export the client and database for easy importing
    client = db_connection.client
    database = db_connection.database

# Collection shortcuts for common use
chat_collection = database["chat_sessions"]
session_titles_collection = database["session_titles"]
users_collection = database["users"]
# Progressive summarization collection
conversation_summaries_collection = database["conversation_summaries"]

def get_database():
    """
    Get database instance
    
    Returns:
        Database: MongoDB database instance
    """
    return database

def get_collection(collection_name: str):
    """
    Get a specific collection
    
    Args:
        collection_name (str): Name of the collection
        
    Returns:
        Collection: MongoDB collection instance
    """
    return database[collection_name]

def check_database_health():
    """
    Check database health and return status
    
    Returns:
        dict: Health status information
    """
    try:
        # Test connection
        client.admin.command('ping')
        
        # Get database stats
        stats = database.command("dbstats")
        
        return {
            "status": "healthy",
            "connected": True,
            "database": DATABASE_NAME,
            "collections": len(database.list_collection_names()),
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