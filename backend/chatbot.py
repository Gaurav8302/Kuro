
"""
AI Chatbot Backend - Main FastAPI Application

This is the main entry point for the AI chatbot backend API.
It provides endpoints for chat functionality, session management, and memory operations.

Features:
- Real-time chat with AI using Google Gemini
- Persistent memory using Pinecone vector database
- Session management with MongoDB
- User isolation and data privacy
- Memory cleanup and summarization
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import os

# Import our custom modules
from memory.ultra_lightweight_memory import store_memory, get_relevant_memories_detailed, ultra_lightweight_memory_manager as memory_manager
from memory.chat_manager import chat_with_memory
from memory.chat_database import (
    get_sessions_by_user, 
    get_chat_by_session, 
    get_all_chats_by_user,
    delete_session_by_id,
    rename_session_title
)
# Temporarily disabled for memory optimization
# from memory.user_profile_api import router as user_profile_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Initialize FastAPI app
app = FastAPI(
    title="AI Chatbot API",
    description="Backend API for AI chatbot with persistent memory",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,  # Hide docs in production
    redoc_url="/redoc" if DEBUG else None  # Hide redoc in production
)

# CORS middleware configuration
# Frontend URLs for production and development
frontend_urls = [
    # Local development
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:4173",  # Vite preview server
    "http://127.0.0.1:4173"
]

# Add production frontend URL if specified
frontend_prod_url = os.getenv("FRONTEND_URL")
if frontend_prod_url:
    frontend_urls.extend([
        frontend_prod_url,
        frontend_prod_url.replace("https://", "http://")
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_urls,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Register user profile endpoints - temporarily disabled for memory optimization
# app.include_router(user_profile_router)

# Session creation endpoint for new chat
from fastapi import Query
from memory.chat_database import create_new_session
@app.post("/session/create", tags=["Sessions"])
async def create_session(user_id: str = Query(...)):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    session_id = create_new_session(user_id)
    if session_id:
        return {"status": "success", "session_id": session_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to create session")

# Pydantic models for request/response validation
class MemoryInput(BaseModel):
    """Request model for storing memory"""
    user_id: str = Field(..., description="Unique identifier for the user")
    text: str = Field(..., description="Text content to store in memory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class QueryInput(BaseModel):
    """Request model for retrieving memory"""
    user_id: str = Field(..., description="Unique identifier for the user")
    query: str = Field(..., description="Query text for memory retrieval")
    top_k: int = Field(default=5, description="Number of memories to retrieve")

class ChatInput(BaseModel):
    """Request model for chat messages"""
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="User's chat message")
    session_id: Optional[str] = Field(None, description="Optional session ID")

class RenameRequest(BaseModel):
    """Request model for renaming sessions"""
    new_title: str = Field(..., description="New title for the session")

# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"message": "AI Chatbot API is running", "status": "healthy"}

# Memory management endpoints
@app.post("/store-memory", tags=["Memory"])
async def store_user_memory(payload: MemoryInput):
    """
    Store user memory in the vector database
    
    This endpoint allows storing text content with metadata in Pinecone
    for later semantic retrieval.
    """
    try:
        # Inject user_id into metadata for user isolation
        payload.metadata["user"] = payload.user_id
        memory_id = store_memory(payload.text, payload.metadata)
        
        logger.info(f"Memory stored for user {payload.user_id}: {memory_id}")
        return {"status": "success", "memory_id": memory_id}
    
    except Exception as e:
        logger.error(f"Error storing memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")

@app.post("/retrieve-memory", tags=["Memory"])
async def retrieve_memories(payload: QueryInput):
    """
    Retrieve relevant memories based on a query
    
    Uses semantic search to find the most relevant stored memories
    for the given user and query.
    """
    try:
        # Get detailed memories with metadata
        memories = get_relevant_memories_detailed(
            query=payload.query, 
            user_filter=payload.user_id, 
            top_k=payload.top_k
        )
        
        # Format for API response (maintain backward compatibility)  
        formatted_memories = [
            {
                "text": memory["text"],
                "score": memory.get("score", 0.0),
                "importance": memory.get("importance", 0.5),
                "category": memory.get("category", "general"),
                "timestamp": memory.get("timestamp", "")
            }
            for memory in memories
        ]
        
        logger.info(f"Retrieved {len(formatted_memories)} memories for user {payload.user_id}")
        return {"query": payload.query, "results": formatted_memories}
    
    except Exception as e:
        logger.error(f"Error retrieving memories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {str(e)}")

# Chat endpoints
@app.post("/chat", tags=["Chat"])
async def chat_endpoint(payload: ChatInput):
    """
    Send a message to the AI chatbot
    
    ARCHITECTURE NOTE:
    - Full chat history is stored in MongoDB (persistent, complete conversations)
    - Pinecone stores semantic memory/context (for AI to remember user preferences, facts, etc.)
    - This endpoint uses both: MongoDB for chat history, Pinecone for personalization
    """
    try:
        reply = chat_with_memory(
            user_id=payload.user_id,
            message=payload.message,
            session_id=payload.session_id
        )
        
        logger.info(f"Chat response generated for user {payload.user_id}")
        return {"reply": reply}
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Session management endpoints
@app.get("/sessions/{user_id}", tags=["Sessions"])
async def get_user_sessions(user_id: str):
    """
    Get all chat sessions for a specific user from MongoDB
    
    Returns a list of sessions with their titles and IDs, ordered by creation date.
    """
    try:
        sessions = get_sessions_by_user(user_id)
        
        logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
        return {"user_id": user_id, "sessions": sessions}
    
    except Exception as e:
        logger.error(f"Error retrieving sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")

@app.get("/chat/{session_id}", tags=["Sessions"])
async def get_session_chat(session_id: str):
    """
    Get full chat history for a specific session from MongoDB
    
    This retrieves the complete conversation history stored in MongoDB,
    NOT from Pinecone (which is only used for semantic memory/context).
    Returns all messages in chronological order for the given session.
    """
    try:
        chat_history = get_chat_by_session(session_id)
        
        logger.info(f"Retrieved chat history for session {session_id}")
        return {"session_id": session_id, "history": chat_history}
    
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")

@app.get("/history/{user_id}", tags=["Sessions"])
async def get_user_chat_history(user_id: str):
    """
    Get complete chat history for a user across all sessions
    
    Returns all chat messages for the user, organized by session.
    """
    try:
        full_history = get_all_chats_by_user(user_id)
        
        logger.info(f"Retrieved full history for user {user_id}")
        return {"user_id": user_id, "history": full_history}
    
    except Exception as e:
        logger.error(f"Error retrieving user history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user history: {str(e)}")

@app.put("/session/{session_id}", tags=["Sessions"])
async def rename_session(session_id: str, request: RenameRequest):
    """
    Rename a chat session
    
    Updates the title of the specified session.
    """
    try:
        success = rename_session_title(session_id, request.new_title)
        
        if success:
            logger.info(f"Session {session_id} renamed to: {request.new_title}")
            return {"message": "Session renamed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found or rename failed")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to rename session: {str(e)}")

@app.delete("/session/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    """
    Delete a chat session
    
    Removes all messages and data associated with the specified session.
    """
    try:
        success = delete_session_by_id(session_id)
        
        if success:
            logger.info(f"Session {session_id} deleted successfully")
            return {"status": "success", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Session not found or already deleted")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@app.post("/session/summarize/{session_id}", tags=["Sessions"])
async def summarize_session(session_id: str, user_id: str):
    """
    Summarize and cleanup a chat session
    
    Creates a summary of the session and removes detailed chat history
    to optimize memory usage while preserving important information.
    """
    try:
        # Temporarily disabled - session_cleanup module not available
        # from memory.session_cleanup import summarize_and_cleanup_session
        # result = await summarize_and_cleanup_session(session_id, user_id)
        
        logger.info(f"Session summarization requested for {session_id} (temporarily disabled)")
        return {"status": "success", "message": "Session summarization is temporarily disabled"}
    
    except Exception as e:
        logger.error(f"Error summarizing session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize session: {str(e)}")

# Enhanced Memory Management endpoints
@app.get("/user/{user_id}/context", tags=["Memory"])
async def get_user_context(user_id: str):
    """
    Get comprehensive user context including name, preferences, goals, etc.
    
    This endpoint provides a complete overview of what the AI knows about the user.
    """
    try:
        context = memory_manager.get_user_context(user_id)
        
        logger.info(f"Retrieved context for user {user_id}")
        return {"user_id": user_id, "context": context}
    
    except Exception as e:
        logger.error(f"Error retrieving user context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user context: {str(e)}")

@app.post("/user/{user_id}/cleanup", tags=["Memory"])
async def cleanup_user_memories(user_id: str, days_threshold: int = 30):
    """
    Clean up old, low-importance memories for a user
    
    This helps maintain optimal performance by removing outdated information
    while preserving important memories.
    """
    try:
        memory_manager.cleanup_old_memories(user_id, days_threshold)
        
        logger.info(f"Cleaned up memories for user {user_id} (threshold: {days_threshold} days)")
        return {"status": "success", "user_id": user_id, "days_threshold": days_threshold}
    
    except Exception as e:
        logger.error(f"Error cleaning up memories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup memories: {str(e)}")

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring system status
    """
    try:
        # Test Pinecone connection
        stats = memory_manager.index.describe_index_stats()
        
        return {
            "status": "healthy",
            "components": {
                "api": "operational",
                "pinecone": "connected",
                "vector_count": stats.total_vector_count if stats else 0
            }
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "error": str(e)
        }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} error: {exc.detail}")
    return {"error": exc.detail, "status_code": exc.status_code}

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    logger.warning(f"404 Not Found: {request.url}")
    return {"error": "Endpoint not found", "detail": "The requested resource was not found"}

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(exc)}", exc_info=True)
    return {"error": "Internal server error", "detail": "Something went wrong on our end"}

if __name__ == "__main__":
    import uvicorn
    
    # Environment-based configuration
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Starting AI Chatbot API on {host}:{port}")
    print(f"📝 Environment: {'Production' if IS_PRODUCTION else 'Development'}")
    
    uvicorn.run(
        app, 
        host=host, 
        port=port, 
        reload=not IS_PRODUCTION,  # Disable reload in production
        access_log=True,
        log_level="info"
    )