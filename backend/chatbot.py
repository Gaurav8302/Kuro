
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
import signal
import sys
import atexit
from contextlib import asynccontextmanager

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
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import os

# Import our custom modules
# v3 memory system
from memory.chat_manager_v3 import ChatManagerV3
chat_manager_v3_instance = ChatManagerV3()
from memory.chat_database import save_chat_to_db
from memory.chat_database import (
    get_sessions_by_user, 
    get_chat_by_session, 
    get_all_chats_by_user,
    delete_session_by_id,
    rename_session_title
)
# Keep legacy Pinecone manager for /store-memory, /retrieve-memory, /health endpoints
from memory.ultra_lightweight_memory import (
    store_memory,
    get_relevant_memories_detailed,
    ultra_lightweight_memory_manager as memory_manager,
)

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

# --- Graceful Shutdown Handling ---
_shutdown_handlers = []

def register_shutdown_handler(handler):
    """Register a function to be called during shutdown"""
    _shutdown_handlers.append(handler)

def graceful_shutdown(signum=None, frame=None):
    """Handle graceful shutdown"""
    logger.info(f"🛑 Graceful shutdown initiated (signal: {signum})")
    
    # Call all registered shutdown handlers
    for handler in _shutdown_handlers:
        try:
            handler()
        except Exception as e:
            logger.error(f"❌ Shutdown handler error: {e}")
    
    # Close database connections
    try:
        from database.db import get_database_connection
        db_conn = get_database_connection()
        db_conn.close_connection()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Database cleanup error: {e}")
    
    logger.info("👋 Shutdown complete")

# Register signal handlers for graceful shutdown
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    try:
        signal.signal(signal.SIGTERM, graceful_shutdown)
        signal.signal(signal.SIGINT, graceful_shutdown)
        atexit.register(lambda: graceful_shutdown(signum="ATEXIT"))
        logger.info("✅ Signal handlers registered")
    except Exception as e:
        logger.warning(f"⚠️ Could not register signal handlers: {e}")

setup_signal_handlers()

# Fast startup signal
@app.on_event("startup")
async def _startup_log():
    logger.info("🚀 FastAPI startup complete - readiness signal")

# --- Observability / Instrumentation Registration (Step 1+) ---
try:
    from observability.instrumentation_middleware import register_instrumentation
    register_instrumentation(app)
except Exception as _obs_err:
    logger.warning(f"Instrumentation middleware registration failed: {_obs_err}")

# --- Sentry Initialization (Step 7 Alerts) ---
if os.getenv("SENTRY_DSN"):
    try:
        import sentry_sdk  # type: ignore
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            enable_tracing=os.getenv("SENTRY_ENABLE_TRACING", "false").lower() in {"1","true","yes"}
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")

# --- Admin Router (Step 6) ---
try:
    from admin.router import router as admin_router
    app.include_router(admin_router)
except Exception as e:
    logger.warning(f"Admin router not mounted: {e}")

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
    # Add wildcard pattern for Vercel deployments
    "https://kuro.vercel.app",
    "https://kuro.vercel.app/",
]

"""
Allow dynamic CORS for Vercel preview deployments and custom domains:
- FRONTEND_URL: single canonical prod domain (e.g., https://your-app.vercel.app)
- FRONTEND_URL_PATTERN: optional substring to match (e.g., .vercel.app) for preview URLs
"""
frontend_prod_url = os.getenv("FRONTEND_URL")
frontend_url_pattern = os.getenv("FRONTEND_URL_PATTERN", ".vercel.app")  # Default pattern for Vercel
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
    
    # Debug logging for CORS issues
    if origin:
        logger.info(f"🌐 CORS request from origin: {origin}")
        logger.info(f"📋 Allowed origins: {frontend_urls}")
    
    # Precompute allow_origin for this request
    allow_origin = False
    if origin:
        if origin in frontend_urls:
            allow_origin = True
            logger.info(f"✅ Origin allowed (exact match): {origin}")
        elif frontend_url_pattern and frontend_url_pattern in origin:
            allow_origin = True
            logger.info(f"✅ Origin allowed (pattern match): {origin}")
        else:
            logger.warning(f"❌ Origin not allowed: {origin}")

    # Handle preflight OPTIONS requests
    if method == "OPTIONS":
        logger.info(f"🔍 Handling OPTIONS preflight request from {origin}")
        response = Response(status_code=200)
        if allow_origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
            response.headers["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, cache-control, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-clerk-auth-version, x-clerk-session-id"
            response.headers["Access-Control-Max-Age"] = "86400"
            logger.info(f"✅ CORS headers added for OPTIONS: {origin}")
        else:
            logger.warning(f"❌ CORS denied for OPTIONS: {origin}")
        return response
    
    response = await call_next(request)
    
    # Add CORS headers to all responses
    if allow_origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, cache-control, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, x-clerk-auth-version, x-clerk-session-id"
    
    return response

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics exposition endpoint."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        data = generate_latest()  # type: ignore
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        return PlainTextResponse(str(e), status_code=500)

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
def create_session(
    user_id: str = Query(...),
    force_new: bool = Query(False, description="Force creation of a new session even if an empty one exists")
):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    # Before creating a new session, summarize the user's most recent non-empty
    # session so its content is available for cross-session memory retrieval.
    try:
        _auto_summarize_previous_session(user_id)
    except Exception as e:
        logger.warning("Auto-summarize of previous session failed (non-blocking): %s", e)

    session_id = create_new_session(user_id, force_new=force_new)
    if session_id:
        return {"status": "success", "session_id": session_id, "reused": not force_new}
    else:
        raise HTTPException(status_code=500, detail="Failed to create session")


def _auto_summarize_previous_session(user_id: str):
    """Find the user's most recent session with messages and summarize it
    into Pinecone (long-term memory) if not already summarized.
    Runs in a background thread to avoid blocking the session creation response."""
    import threading

    def _do_summarize():
        try:
            from memory.chat_database import get_sessions_by_user
            from memory.session_memory import session_memory
            from memory.long_term_memory import long_term_memory

            sessions = get_sessions_by_user(user_id)
            if not sessions:
                return

            # Find the most recent session that has messages
            for session_info in sessions:
                sid = session_info.get("session_id", "")
                msg_count = session_memory.get_message_count(sid)
                if msg_count >= 4:  # Need at least 4 exchanges to be worth summarizing
                    messages = session_memory.get_recent_messages(sid, limit=200)
                    if messages:
                        summary = long_term_memory.summarize_session(
                            user_id=user_id,
                            session_id=sid,
                            messages=messages,
                        )
                        if summary:
                            logger.info(
                                "Auto-summarized previous session %s for user %s (%d chars)",
                                sid, user_id, len(summary),
                            )
                        return  # Only summarize the most recent non-empty session
        except Exception as e:
            logger.error("Background auto-summarization failed: %s", e)

    thread = threading.Thread(target=_do_summarize, daemon=True)
    thread.start()

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
    model: Optional[str] = Field(None, description="Optional model override")
    search_mode: bool = Field(False, description="Force web search via compound research")
    skill: str = Field("auto", description="Skill override: auto, code, explain, creative, problem, web")

class ChatResponse(BaseModel):
    """Response model for chat messages"""
    reply: str = Field(..., description="AI's response")
    model: Optional[str] = Field(None, description="Model used for this response")
    route_rule: Optional[str] = Field(None, description="Routing rule applied")
    latency_ms: Optional[int] = Field(None, description="Response latency in milliseconds")
    intents: Optional[list] = Field(None, description="Classified intents")
    suggest_search: bool = Field(False, description="True when the response suggests enabling browser search")

class RenameRequest(BaseModel):
    """Request model for renaming sessions"""
    new_title: str = Field(..., description="New title for the session")

# Health check endpoints
@app.head("/")
async def root_head():
    return Response(status_code=200)

@app.get("/", tags=["Health"])
async def root():
    return {"message": "AI Chatbot API is running", "status": "healthy"}

@app.get("/healthz", tags=["Health"])
async def healthz():
    return {"status": "ok"}

@app.get("/live", tags=["Health"])
async def live():
    return {"live": True}

@app.get("/ready", tags=["Health"])
async def ready():
    # Extend with dependency readiness checks if needed
    return {"ready": True}

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

@app.get("/healthz", tags=["Health"])
async def healthz():
    """Lightweight health probe endpoint (no external calls)."""
    return {"status": "ok"}

@app.get("/api-status", tags=["Health"])
async def api_status():
    """
    Check if the Groq API is available or if we've hit rate limits.
    Frontend can use this to show appropriate messages.
    """
    try:
        # Import adjusted to work whether run as module or script
        try:
            from backend.utils.groq_client import GroqClient  # type: ignore
        except ImportError:
            from utils.groq_client import GroqClient  # type: ignore
        
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
def set_user_name_endpoint(user_id: str, request: SetNameRequest):
    """Set user name"""
    try:
        from memory.user_profile import set_user_name
        set_user_name(user_id, request.name)
        return {"status": "success", "message": f"Name set to {request.name}"}
    except Exception as e:
        logger.error(f"Error setting user name: {str(e)}")
        return {"status": "success", "message": "Name processing completed"}  # Always success to avoid breaking chat

@app.get("/user/{user_id}/name", tags=["Users"])
def get_user_name_endpoint(user_id: str):
    """Get user name"""
    try:
        from memory.user_profile import get_user_name
        name = get_user_name(user_id)
        return {"user_id": user_id, "name": name}
    except Exception as e:
        logger.error(f"Error getting user name: {str(e)}")
        return {"user_id": user_id, "name": None}

@app.get("/user/{user_id}/has-name", tags=["Users"])
def check_user_has_name(user_id: str):
    """Check if user has set their name"""
    try:
        from memory.user_profile import get_user_name
        name = get_user_name(user_id)
        return {"user_id": user_id, "has_name": bool(name)}
    except Exception as e:
        logger.error(f"Error checking user name: {str(e)}")
        return {"user_id": user_id, "has_name": False}

# Intro shown persistence endpoints
class IntroShownRequest(BaseModel):
    """Request model for marking intro as shown"""
    shown: bool = Field(default=True, description="Whether intro was shown")

@app.get("/user/{user_id}/intro-shown", tags=["Users"])
def get_intro_shown_endpoint(user_id: str):
    """Return whether the welcome intro was already displayed."""
    try:
        from memory.user_profile import get_intro_shown
        shown = get_intro_shown(user_id)
        return {"user_id": user_id, "intro_shown": shown}
    except Exception as e:
        logger.error(f"Error retrieving intro_shown: {str(e)}")
        return {"user_id": user_id, "intro_shown": False}

@app.post("/user/{user_id}/intro-shown", tags=["Users"])
def set_intro_shown_endpoint(user_id: str, body: IntroShownRequest):
    """Mark intro as shown (idempotent)."""
    if not body.shown:
        return {"status": "ignored", "reason": "Only true is accepted"}
    try:
        from memory.user_profile import set_intro_shown
        set_intro_shown(user_id)
        return {"status": "success", "user_id": user_id, "intro_shown": True}
    except Exception as e:
        logger.error(f"Error setting intro_shown: {str(e)}")
        return {"status": "error", "message": "Failed to persist intro flag"}

# Memory management endpoints
@app.post("/store-memory", tags=["Memory"])
def store_user_memory(payload: MemoryInput):
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
def retrieve_memories(payload: QueryInput):
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
@app.post("/chat", tags=["Chat"], response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatInput):
    """
    Send a message to the AI chatbot.

    Architecture (v2 — minimal deterministic memory):
      Layer 1: Last N raw messages from MongoDB (no compression during active session).
      Layer 2: Post-session summary in Pinecone (only when session ≥ 50 msgs or closes).
      Model lock: same model reused throughout a session to prevent behavioural drift.
    """
    import time as _time
    request_start = _time.time()
    try:
        response_data = await chat_manager_v3_instance.handle_chat(
            user_id=chat_message.user_id,
            session_id=chat_message.session_id or "default",
            user_input=chat_message.message,
            chat_history=[]
        )
        response_text = response_data.get("response", "")
        model_used = response_data.get("model", "v3_model")
        route_rule = response_data.get("route_rule", "v3_rule")

        latency_ms = int((_time.time() - request_start) * 1000)
        logger.info(
            "Chat response for user %s in %dms (model=%s rule=%s)",
            chat_message.user_id, latency_ms, model_used, route_rule,
        )

        # Detect if the response is a safety-triggered browser suggestion
        _is_safety_response = route_rule and (
            "time_sensitive" in route_rule or "verified_blocked" in route_rule
        )

        return ChatResponse(
            reply=response_text,
            model=model_used,
            route_rule=route_rule,
            latency_ms=latency_ms,
            intents=None,
            suggest_search=bool(_is_safety_response),
        )

    except Exception as e:
        logger.error("Error in chat endpoint: %s", e, exc_info=True)
        from memory.hardcoded_responses import get_fallback_response
        return ChatResponse(
            reply=get_fallback_response("generic_error"),
            model="fallback",
            route_rule="error_fallback",
        )

# Session management endpoints
@app.get("/sessions/{user_id}", tags=["Sessions"])
def get_user_sessions(user_id: str):
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
def get_session_chat(session_id: str):
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
def get_user_chat_history(user_id: str):
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
def rename_session(session_id: str, request: RenameRequest):
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
def delete_session(session_id: str):
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
def summarize_session(session_id: str, user_id: str):
    """
    Generate a post-session summary and store in Pinecone (Layer 2).

    Call this when a session is considered "closed" or when the user
    explicitly wants to archive their conversation context.
    """
    try:
        from memory.session_memory import session_memory
        from memory.long_term_memory import long_term_memory

        messages = session_memory.get_recent_messages(session_id, limit=200)
        if len(messages) < 4:
            return {"status": "skipped", "reason": "Session too short to summarize"}

        summary = long_term_memory.summarize_session(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
        )
        if summary:
            logger.info("Session %s summarized (%d chars)", session_id, len(summary))
            return {"status": "success", "summary_length": len(summary)}
        else:
            return {"status": "error", "message": "Summarization returned empty result"}

    except Exception as e:
        logger.error("Error summarizing session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to summarize session: {e}")

# Enhanced Memory Management endpoints
@app.get("/user/{user_id}/context", tags=["Memory"])
def get_user_context(user_id: str):
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
def cleanup_user_memories(user_id: str, days_threshold: int = 30):
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

# --- Inline Ask (ephemeral side-question, READ-ONLY memory) ---

class InlineQueryInput(BaseModel):
    """Request model for inline (ephemeral) side-questions.

    Reads session context but never writes to memory or database.
    """
    selected_text: str = Field(..., description="Text the user selected in a chat message")
    context: str = Field("", description="Surrounding context from the message (~100 tokens)")
    question: str = Field(..., description="User's question about the selected text")
    parent_message: str = Field("", description="Full parent AI response containing the selected text")
    session_id: Optional[str] = Field(None, description="Current session ID for read-only context")
    user_id: Optional[str] = Field(None, description="User ID for session summary lookup")
    message_index: Optional[int] = Field(None, description="Index of the selected message in history (for old-message context)")

class InlineQueryResponse(BaseModel):
    """Response model for inline queries"""
    answer: str = Field(..., description="AI explanation")

@app.post("/inline-query", tags=["Chat"], response_model=InlineQueryResponse)
def inline_query_endpoint(payload: InlineQueryInput):
    """
    Ephemeral endpoint for inline side-questions with READ-ONLY session context.

    This READS:
    - Recent session messages (last 8 exchanges)
    - Session summaries (from long-term memory, if available)

    This does NOT:
    - Store any result in the database
    - Update memory or summaries
    - Affect the main chat flow in any way
    """
    import time as _time
    request_start = _time.time()
    try:
        from utils.groq_client import GroqClient

        # --- Read-only context assembly ---
        recent_messages_text = ""
        session_summary_text = ""

        # 1. Load recent session messages (read-only, last 8 exchanges)
        if payload.session_id:
            try:
                from memory.session_memory import session_memory
                raw_messages = session_memory.get_recent_messages(
                    payload.session_id, limit=8
                )

                # If message_index is provided and points to an older message,
                # use surrounding messages instead of the most recent ones
                if payload.message_index is not None and len(raw_messages) > 0:
                    # Each exchange produces 2 entries (user + assistant)
                    # Get all messages for the session to find context around the selected one
                    from memory.chat_database import chat_db
                    all_docs = list(
                        chat_db.chat_collection.find(
                            {"session_id": payload.session_id}
                        ).sort("metadata.sequence_number", 1)
                    )
                    total_exchanges = len(all_docs)
                    selected_exchange_idx = payload.message_index // 2  # approximate exchange index
                    latest_exchange_idx = total_exchanges - 1

                    # If the selected message is far from the latest (>5 exchanges away),
                    # use surrounding context instead of recent messages
                    if latest_exchange_idx - selected_exchange_idx > 5:
                        start = max(0, selected_exchange_idx - 2)
                        end = min(total_exchanges, selected_exchange_idx + 3)
                        surrounding_docs = all_docs[start:end]
                        surrounding_messages = []
                        for doc in surrounding_docs:
                            user_msg = doc.get("message", "")
                            assistant_msg = doc.get("reply", "")
                            if user_msg:
                                surrounding_messages.append({"role": "user", "content": user_msg})
                            if assistant_msg:
                                surrounding_messages.append({"role": "assistant", "content": assistant_msg})
                        raw_messages = surrounding_messages

                if raw_messages:
                    lines = []
                    for m in raw_messages:
                        role = m.get("role", "user").capitalize()
                        content = m.get("content", "")
                        # Truncate individual messages to ~150 tokens (~600 chars)
                        if len(content) > 600:
                            content = content[:597] + "..."
                        lines.append(f"{role}: {content}")
                    recent_messages_text = "\n".join(lines)
            except Exception as e:
                logger.warning("Inline query: failed to load session messages: %s", e)

        # 2. Load session summary (read-only, from long-term memory)
        if payload.user_id and payload.session_id:
            try:
                from memory.long_term_memory import long_term_memory
                summaries = long_term_memory.retrieve(
                    payload.selected_text, payload.user_id, top_k=1
                )
                if summaries:
                    session_summary_text = summaries[0].get("text", "")
                    # Cap summary to ~200 tokens (~800 chars)
                    if len(session_summary_text) > 800:
                        session_summary_text = session_summary_text[:797] + "..."
            except Exception as e:
                logger.warning("Inline query: failed to load session summary: %s", e)

        # --- Build prompt with full context ---
        system_instruction = (
            "You are Kuro, a helpful AI assistant. The user is reading an AI response "
            "inside a conversation and selected a piece of text they want clarification about. "
            "Explain clearly and concisely so the user understands the concept in the context "
            "of the ongoing discussion."
        )

        prompt_parts = []
        prompt_parts.append(f"Selected text:\n{payload.selected_text}")

        if payload.parent_message:
            # Cap parent message to ~300 tokens (~1200 chars)
            parent = payload.parent_message
            if len(parent) > 1200:
                parent = parent[:1197] + "..."
            prompt_parts.append(f"Full response containing the text:\n{parent}")
        elif payload.context:
            prompt_parts.append(f"Context from the message:\n{payload.context}")

        if recent_messages_text:
            prompt_parts.append(f"Conversation context:\n{recent_messages_text}")

        if session_summary_text:
            prompt_parts.append(f"Session summary:\n{session_summary_text}")

        prompt_parts.append(f"User question:\n{payload.question}")

        prompt = "\n\n".join(prompt_parts)

        client = GroqClient()
        answer = client.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
        )

        latency_ms = int((_time.time() - request_start) * 1000)
        logger.info("Inline query answered in %dms (session_ctx=%s)", latency_ms, bool(payload.session_id))
        return InlineQueryResponse(answer=answer)

    except Exception as e:
        logger.error("Inline query failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate inline answer")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} error: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    logger.warning(f"404 Not Found: {request.url}")
    return JSONResponse(status_code=404, content={"error": "Endpoint not found", "detail": "The requested resource was not found"})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": "Something went wrong on our end"})

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