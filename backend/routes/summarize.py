from fastapi import APIRouter
from backend.memory.session_cleanup import summarize_and_cleanup_session

router = APIRouter()

@router.post("/session/{session_id}/summarize")
async def summarize_session(session_id: str, user_id: str):
    result = await summarize_and_cleanup_session(session_id, user_id)
    return result
