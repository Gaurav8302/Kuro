from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Path, Query, HTTPException, Header, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

# Import backend modules
from backend.memory.memory_manager import store_memory, get_relevant_memories
from backend.memory.chat_manager import chat_with_memory
from backend.memory.chat_database import (
    get_sessions_by_user,
    get_chat_by_session,
    get_all_chats_by_user,
    delete_session_by_id,
    rename_session_title,
    create_new_session
)
from backend.database.db import database
import requests
import os

app = FastAPI()

# Clerk JWT verification
def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Invalid authorization header')
    token = authorization.split(' ')[1]
    clerk_secret = os.getenv('CLERK_SECRET_KEY')
    resp = requests.get(
        'https://api.clerk.dev/v1/tokens/verify',
        headers={
            'Authorization': f'Bearer {clerk_secret}',
            'Content-Type': 'application/json'
        },
        json={ 'token': token }
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail='Invalid Clerk token')
    user_id = resp.json().get('sub') or resp.json().get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail='User ID not found in Clerk token')
    return user_id

# CORS setup for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class MemoryInput(BaseModel):
    user_id: str
    text: str
    metadata: dict

class QueryInput(BaseModel):
    user_id: str
    query: str
    top_k: int = 5

class ChatInput(BaseModel):
    user_id: str
    message: str

class RenameRequest(BaseModel):
    new_title: str

# --- Endpoints ---
# User creation (SignUp)
@app.post("/users/create")
async def create_user(user_id: str = Depends(get_current_user)):
    users_collection = database["users"]
    existing = users_collection.find_one({"user_id": user_id})
    if existing:
        return JSONResponse(status_code=200, content={"status": "exists", "user_id": user_id})
    users_collection.insert_one({"user_id": user_id, "created_at": datetime.utcnow()})
    return {"status": "created", "user_id": user_id}

# Session creation
@app.post("/session/create")
async def create_session(user_id: str = Query(...)):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    session_id = create_new_session(user_id)
    if session_id:
        return {"status": "success", "session_id": session_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to create session")

# Get user sessions
@app.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    sessions = get_sessions_by_user(user_id)
    return {"user_id": user_id, "sessions": sessions}

# Get chat history for a session
@app.get("/chat/{session_id}")
async def get_session_chat(session_id: str):
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    chat_history = get_chat_by_session(session_id)
    return {"session_id": session_id, "history": chat_history}

# Get all chat history for a user
@app.get("/history/{user_id}")
async def get_user_chat_history(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    full_history = get_all_chats_by_user(user_id)
    return {"user_id": user_id, "history": full_history}

# Store memory
@app.post("/store-memory")
async def store_user_memory(payload: MemoryInput):
    if not payload.user_id or not payload.text:
        raise HTTPException(status_code=400, detail="Missing user_id or text")
    payload.metadata["user"] = payload.user_id
    try:
        memory_id = store_memory(payload.text, payload.metadata)
        return {"status": "success", "memory_id": memory_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Retrieve memory
@app.post("/retrieve-memory")
async def retrieve_memories(payload: QueryInput):
    if not payload.user_id or not payload.query:
        raise HTTPException(status_code=400, detail="Missing user_id or query")
    memories = get_relevant_memories(payload.query, payload.user_id, payload.top_k)
    return {"query": payload.query, "results": memories}

# Chat endpoint
@app.post("/chat")
async def chat_endpoint(payload: ChatInput):
    if not payload.user_id or not payload.message:
        raise HTTPException(status_code=400, detail="Missing user_id or message")
    try:
        reply = chat_with_memory(user_id=payload.user_id, message=payload.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete session
@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    success = delete_session_by_id(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or already deleted.")
    return {"status": "success", "session_id": session_id}

# Rename session
@app.put("/session/{session_id}")
async def rename_session(session_id: str, request: RenameRequest):
    if not session_id or not request.new_title:
        raise HTTPException(status_code=400, detail="Missing session_id or new_title")
    success = rename_session_title(session_id, request.new_title)
    if success:
        return {"message": "Session renamed successfully."}
    else:
        raise HTTPException(status_code=404, detail="Session not found or rename failed.")

# Summarize session
@app.post("/session/summarize/{session_id}")
async def summarize_session(session_id: str, user_id: str = Query(...)):
    if not session_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing session_id or user_id")
    try:
        from backend.memory.session_cleanup import summarize_and_cleanup_session
        result = await summarize_and_cleanup_session(session_id, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
