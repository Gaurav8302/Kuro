"""
User Profile API endpoints for name management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.memory.user_profile import get_user_name, set_user_name

router = APIRouter()

class NameRequest(BaseModel):
    user_id: str
    name: str

@router.get("/user/name/{user_id}")
def api_get_user_name(user_id: str):
    name = get_user_name(user_id)
    if name:
        return {"user_id": user_id, "name": name}
    raise HTTPException(status_code=404, detail="Name not found")

@router.post("/user/name")
def api_set_user_name(req: NameRequest):
    set_user_name(req.user_id, req.name)
    return {"status": "success", "user_id": req.user_id, "name": req.name}
