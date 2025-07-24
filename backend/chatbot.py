
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

# Import our custom modules

from backend.memory.memory_manager import store_memory, get_relevant_memories
from backend.memory.chat_manager import chat_with_memory
from backend.memory.chat_database import (
    get_sessions_by_user, 
    get_chat_by_session, 
    get_all_chats_by_user,
    delete_session_by_id,
    rename_session_title
)
from backend.memory.user_profile_api import router as user_profile_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Chatbot API",
    description="Backend API for AI chatbot with persistent memory",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ],  # Frontend URLs (React/Vite dev server)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register user profile endpoints
# Register user profile endpoints
app.include_router(user_profile_router)

# Session creation endpoint for new chat
from fastapi import Query
from backend.memory.chat_database import create_new_session
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

# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"message": "AI Chatbot API is running", "status": "healthy"}

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Chatbot Backend",
        "version": "1.0.0"
    }

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
        memories = get_relevant_memories(payload.query, payload.user_id, payload.top_k)
        
        logger.info(f"Retrieved {len(memories)} memories for user {payload.user_id}")
        return {"query": payload.query, "results": memories}
    
    except Exception as e:
        logger.error(f"Error retrieving memories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {str(e)}")

# Chat endpoints
@app.post("/chat", tags=["Chat"])
async def chat_endpoint(payload: ChatInput):
    """
    Send a message to the AI chatbot
    
    The AI will use stored memories and context to provide personalized responses.
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
    Get all chat sessions for a specific user
    
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
    Get chat history for a specific session
    
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
        from backend.memory.session_cleanup import summarize_and_cleanup_session
        
        result = await summarize_and_cleanup_session(session_id, user_id)
        
        logger.info(f"Session {session_id} summarized and cleaned up")
        return result
    
    except Exception as e:
        logger.error(f"Error summarizing session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize session: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return {"error": "Endpoint not found", "detail": exc.detail}

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc.detail}")
    return {"error": "Internal server error", "detail": "Something went wrong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)