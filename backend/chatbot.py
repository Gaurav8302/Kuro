
"""
AI Chatbot Backend - Main FastAPI Application

This is the main entry point for the AI chatbot backend API.
It provides endpoints for chat functionality, session management, and memory operations.

Features:
- Real-time chat with AI using Groq LLaMA 3 70B
- Persistent memory using Pinecone vector database
- Session management with MongoDB
- User isolation and data privacy
- Memory cleanup and summarization
"""

from dotenv import load_dotenv
load_dotenv()

import os
import logging

# Validate critical environment variables on startup
required_env_vars = ["GROQ_API_KEY", "GEMINI_API_KEY", "PINECONE_API_KEY", "MONGODB_URI"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Missing environment variables: {missing_vars}")
    # Don't raise error in production to allow graceful degradation
    if os.getenv("ENVIRONMENT") != "production":
        raise RuntimeError(f"Missing required environment variables: {missing_vars}")

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import os

# Import our custom modules
from memory.long_context_memory_manager import chat_with_long_context_memory, long_context_memory_manager, summarize_session_background
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

# Startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize long-context memory manager
        if IS_PRODUCTION:
            logger.info("🚀 Initializing long-context memory system for production")
        else:
            logger.info("💡 Long-context memory system initialized for development")
        
        logger.info("✅ Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")

# Shutdown event to cleanup services
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    try:
        logger.info("✅ Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Frontend URLs for CORS configuration
frontend_urls = [
    # Local development
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:4173",  # Vite preview server
    "http://127.0.0.1:4173",
    # Production frontend URLs
    "https://kuro-tau.vercel.app",
    "https://kuro-tau.vercel.app/",
]

# Add additional production frontend URL if specified via environment variable
frontend_prod_url = os.getenv("FRONTEND_URL")
if frontend_prod_url:
    frontend_urls.extend([
        frontend_prod_url,
        frontend_prod_url.replace("https://", "http://")
    ])

# CORS middleware for production stability
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    """Handle CORS requests with manual headers for reliability"""
    origin = request.headers.get("origin")
    method = request.method
    
    # Handle preflight OPTIONS requests
    if method == "OPTIONS":
        response = Response(status_code=200)
        if origin and origin in frontend_urls:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
            response.headers["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-clerk-auth-version, x-clerk-session-id"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response
    
    response = await call_next(request)
    
    # Add CORS headers to all responses
    if origin and origin in frontend_urls:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-clerk-auth-version, x-clerk-session-id"
    
    return response

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
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

@app.get("/ping", tags=["Health"])
async def ping():
    """
    Auto-warm ping endpoint to keep the server awake.
    Called by frontend every 4.5 minutes to prevent Render from sleeping.
    """
    from datetime import datetime
    return {
        "status": "ok", 
        "message": "Server is awake and healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_check": "render_auto_warm"
    }

@app.get("/api-status", tags=["Health"])
async def api_status():
    """
    Check if the Groq API is available or if we've hit rate limits.
    Frontend can use this to show appropriate messages.
    """
    try:
        from backend.utils.groq_client import GroqClient
        
        # Test with a minimal request
        groq_client = GroqClient()
        test_response = groq_client.generate_response(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1
        )
        
        return {
            "status": "available",
            "message": "AI chat is available",
            "quota_status": "ok"
        }
        
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            return {
                "status": "quota_exceeded", 
                "message": "AI chat temporarily unavailable due to daily quota limit",
                "quota_status": "exceeded",
                "reset_info": "Quota resets every 24 hours"
            }
        else:
            return {
                "status": "error",
                "message": "AI service temporarily unavailable", 
                "quota_status": "unknown"
            }

# User name management endpoints
class SetNameRequest(BaseModel):
    """Request model for setting user name"""
    name: str = Field(..., description="User's name")

@app.post("/user/{user_id}/set-name", tags=["Users"])
async def set_user_name_endpoint(user_id: str, request: SetNameRequest):
    """Set user name"""
    try:
        from memory.user_profile import set_user_name
        set_user_name(user_id, request.name)
        return {"status": "success", "message": f"Name set to {request.name}"}
    except Exception as e:
        logger.error(f"Error setting user name: {str(e)}")
        return {"status": "success", "message": "Name processing completed"}  # Always success to avoid breaking chat

@app.get("/user/{user_id}/name", tags=["Users"])
async def get_user_name_endpoint(user_id: str):
    """Get user name"""
    try:
        from memory.user_profile import get_user_name
        name = get_user_name(user_id)
        return {"user_id": user_id, "name": name}
    except Exception as e:
        logger.error(f"Error getting user name: {str(e)}")
        return {"user_id": user_id, "name": None}

@app.get("/user/{user_id}/has-name", tags=["Users"])
async def check_user_has_name(user_id: str):
    """Check if user has set their name"""
    try:
        from memory.user_profile import get_user_name
        name = get_user_name(user_id)
        return {"user_id": user_id, "has_name": bool(name)}
    except Exception as e:
        logger.error(f"Error checking user name: {str(e)}")
        return {"user_id": user_id, "has_name": False}

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
        
        # Store memory using long-context system
        # For now, we'll use the basic text storage and let the system
        # handle it through automatic summarization
        memory_id = f"manual_{payload.user_id}_{datetime.now().isoformat()}"
        
        # Store in vector database
        embedding = long_context_memory_manager.generate_embedding(payload.text)
        long_context_memory_manager.pinecone_index.upsert([
            (memory_id, embedding, {
                "user_id": payload.user_id,
                "type": "manual_memory",
                "text": payload.text[:1000],  # Truncate for metadata
                "timestamp": datetime.now().isoformat(),
                **payload.metadata
            })
        ])
        
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
        # Get relevant summaries using long-context system
        summaries = long_context_memory_manager.retrieve_relevant_summaries(
            user_id=payload.user_id,
            current_query=payload.query
        )
        
        # Format for API response (maintain backward compatibility)  
        formatted_memories = [
            {
                "text": summary.summary,
                "score": 0.8,  # Placeholder score
                "importance": 0.7,
                "category": "conversation_summary",
                "timestamp": summary.timestamp,
                "key_topics": summary.key_topics,
                "user_preferences": summary.user_preferences,
                "important_facts": summary.important_facts
            }
            for summary in summaries
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
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    try:
        # Add timeout protection to prevent worker timeout
        def sync_chat():
            # Use long-context memory system
            return chat_with_long_context_memory(
                user_id=payload.user_id,
                message=payload.message,
                session_id=payload.session_id
            )
        
        # Run the synchronous chat function in a thread pool with timeout
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                reply = await asyncio.wait_for(
                    loop.run_in_executor(executor, sync_chat),
                    timeout=150.0
                )
            
            logger.info(f"Chat response generated for user {payload.user_id}")
            return {"reply": reply}
            
        except asyncio.TimeoutError:
            logger.warning(f"Chat response timed out for user {payload.user_id}")
            return {"reply": "I apologize, but my response is taking longer than expected. Please try again with a shorter message or try again in a moment."}
    
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
        # Get recent summaries as user context using long-context system
        summaries = long_context_memory_manager.retrieve_relevant_summaries(
            user_id=user_id,
            current_query="user preferences profile goals history"
        )
        
        context = {
            "summaries": [summary.to_dict() for summary in summaries],
            "total_summaries": len(summaries)
        }
        
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
        # Use long-context memory manager for cleanup
        cleaned_count = long_context_memory_manager.cleanup_old_memories(user_id, days_threshold)
        
        logger.info(f"Cleaned up {cleaned_count} memories for user {user_id} (threshold: {days_threshold} days)")
        return {
            "status": "success", 
            "user_id": user_id, 
            "days_threshold": days_threshold,
            "cleaned_count": cleaned_count
        }
    
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
        # Test Pinecone connection using long-context manager
        stats = long_context_memory_manager.pinecone_index.describe_index_stats()
        
        return {
            "status": "healthy",
            "components": {
                "api": "operational",
                "pinecone": "connected",
                "vector_count": stats.total_vector_count if stats else 0,
                "long_context_system": "active"
            },
            "memory_optimization": {
                "max_total_tokens": long_context_memory_manager.MAX_TOTAL_TOKENS,
                "max_context_tokens": long_context_memory_manager.MAX_CONTEXT_TOKENS,
                "stm_message_limit": long_context_memory_manager.STM_MESSAGE_LIMIT,
                "ltm_retrieval_limit": long_context_memory_manager.LTM_RETRIEVAL_LIMIT,
                "model": "llama-3.3-70b-versatile"
            }
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "error": str(e)
        }

# New optimized memory endpoints
@app.post("/session/{session_id}/summarize", tags=["Memory"])
async def summarize_session_endpoint(session_id: str, user_id: str):
    """
    Manually trigger session summarization
    
    This endpoint allows manual summarization of a long session
    for immediate memory optimization.
    """
    try:
        summary = summarize_session_background(session_id)
        
        if summary:
            logger.info(f"Session {session_id} summarized on demand")
            return {
                "status": "success",
                "session_id": session_id,
                "summary": summary.to_dict()
            }
        else:
            return {
                "status": "no_action",
                "session_id": session_id,
                "message": "Session does not need summarization or summarization failed"
            }
    
    except Exception as e:
        logger.error(f"Error in manual session summarization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize session: {str(e)}")

@app.get("/memory/stats", tags=["Memory"])
async def get_memory_stats():
    """
    Get memory system statistics and performance metrics
    """
    try:
        return {
            "optimization_settings": {
                "max_total_tokens": long_context_memory_manager.MAX_TOTAL_TOKENS,
                "max_context_tokens": long_context_memory_manager.MAX_CONTEXT_TOKENS,
                "stm_message_limit": long_context_memory_manager.STM_MESSAGE_LIMIT,
                "ltm_retrieval_limit": long_context_memory_manager.LTM_RETRIEVAL_LIMIT,
                "summarization_threshold": long_context_memory_manager.SUMMARIZATION_THRESHOLD
            },
            "system_info": {
                "model": "llama-3.3-70b-versatile",
                "context_window": "128K tokens",
                "memory_architecture": "two_tier_stm_ltm",
                "vector_database": "pinecone"
            },
            "system_status": "optimized_for_long_context_llama"
        }
    
    except Exception as e:
        logger.error(f"Error retrieving memory stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memory stats: {str(e)}")

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