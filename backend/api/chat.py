"""
Chat API Router — Chat endpoint

Provides the main /chat endpoint for conversational AI.
"""

import os
import time
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


class ChatInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="User's chat message")
    session_id: Optional[str] = Field(None, description="Session ID")
    model: Optional[str] = Field(None, description="Model override")
    skill: str = Field("auto", description="Skill override")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI response")
    model: Optional[str] = None
    route_rule: Optional[str] = None
    latency_ms: Optional[int] = None
    session_id: Optional[str] = None


# Lazy-initialized chat manager
_chat_manager = None


def _get_chat_manager():
    global _chat_manager
    if _chat_manager is None:
        from memory.chat_manager_v3 import ChatManagerV3
        _chat_manager = ChatManagerV3()
    return _chat_manager


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatInput):
    """Send a message to Kuro AI."""
    request_start = time.time()
    try:
        from memory.chat_database import (
            create_new_session, get_chat_by_session, save_chat_to_db,
        )

        effective_session_id = chat_message.session_id
        if not effective_session_id:
            try:
                effective_session_id = create_new_session(chat_message.user_id)
            except Exception:
                effective_session_id = "default"

        # Build chat history from DB
        db_history = get_chat_by_session(effective_session_id)
        chat_history = []
        for turn in db_history[-20:]:
            user_msg = str(turn.get("user", "") or "").strip()
            assistant_msg = str(turn.get("assistant", "") or "").strip()
            if user_msg:
                chat_history.append({"role": "user", "content": user_msg})
            if assistant_msg:
                chat_history.append({"role": "assistant", "content": assistant_msg})

        # Generate response
        manager = _get_chat_manager()
        response_text = await manager.handle_chat(
            user_id=chat_message.user_id,
            session_id=effective_session_id,
            user_input=chat_message.message,
            chat_history=chat_history,
        )

        latency_ms = int((time.time() - request_start) * 1000)

        # Persist to DB
        try:
            persisted = save_chat_to_db(
                user_id=chat_message.user_id,
                message=chat_message.message,
                reply=response_text,
                session_id=effective_session_id,
            )
            effective_session_id = persisted or effective_session_id
        except Exception as e:
            logger.error("Failed to persist chat: %s", e)

        return ChatResponse(
            reply=response_text,
            model="v3_model",
            route_rule="v3_rule",
            latency_ms=latency_ms,
            session_id=effective_session_id,
        )

    except Exception as e:
        logger.error("Chat endpoint error: %s", e, exc_info=True)
        from memory.hardcoded_responses import get_fallback_response
        return ChatResponse(
            reply=get_fallback_response("generic_error"),
            model="fallback",
            route_rule="error_fallback",
        )
