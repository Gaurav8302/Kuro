"""
Sessions API Router — Session management endpoints

Provides session creation, listing, deletion, and renaming.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Sessions"])


class RenameRequest(BaseModel):
    new_title: str = Field(..., description="New title for the session")


@router.post("/create")
def create_session(
    user_id: str = Query(...),
    force_new: bool = Query(False, description="Force new session"),
):
    """Create a new chat session for a user."""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    from memory.chat_database import create_new_session
    session_id = create_new_session(user_id, force_new=force_new)
    if session_id:
        return {"status": "success", "session_id": session_id, "reused": not force_new}
    raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/list")
def list_sessions(user_id: str = Query(...)):
    """List all sessions for a user."""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    from memory.chat_database import get_sessions_by_user
    sessions = get_sessions_by_user(user_id)
    return {"sessions": sessions}


@router.get("/{session_id}/history")
def get_session_history(session_id: str):
    """Get chat history for a session."""
    from memory.chat_database import get_chat_by_session
    history = get_chat_by_session(session_id)
    return {"session_id": session_id, "history": history}


@router.delete("/{session_id}")
def delete_session(session_id: str):
    """Delete a session by ID."""
    from memory.chat_database import delete_session_by_id
    try:
        delete_session_by_id(session_id)
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}/rename")
def rename_session(session_id: str, body: RenameRequest):
    """Rename a session."""
    from memory.chat_database import rename_session_title
    try:
        rename_session_title(session_id, body.new_title)
        return {"status": "success", "session_id": session_id, "new_title": body.new_title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
