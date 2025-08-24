"""Instrumentation middleware for logging LLM orchestration calls (Step 1)."""
from __future__ import annotations
import os
import time
import uuid
import hashlib
import logging
from typing import Callable, Awaitable, Dict, Any
import contextvars
from fastapi import Request, Response

OBS_DISABLED = os.getenv("OBS_DISABLED") == "1"
HEALTH_PATHS = {"/healthz", "/live", "/ready", "/metrics"}

try:
    import structlog  # type: ignore
    _logger = structlog.get_logger()
except Exception:
    _logger = logging.getLogger(__name__)

try:
    from .metrics import observe_request, LLM_ACTIVE_REQUESTS
except Exception:  # metrics optional during early boot
    def observe_request(*args, **kwargs):  # type: ignore
        return None
    class _Dummy:
        def inc(self): pass
        def dec(self): pass
    LLM_ACTIVE_REQUESTS = _Dummy()

try:
    from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
except Exception:
    AsyncIOMotorClient = None  # type: ignore

LOG_RAW = os.getenv("LOG_RAW_CONTENT", "false").lower() in {"1", "true", "yes"}
try:
    from typing import Optional
    _mongo_client: Optional[AsyncIOMotorClient] = None  # type: ignore
except Exception:
    _mongo_client = None  # type: ignore
_db = None
_collection = None

# Context variable for per-request tracing
_current_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_request_id", default=None)

async def init_motor(uri: str | None = None, db_name: str | None = None):
    """Initialize Motor client inside the running event loop (post-fork)."""
    global _mongo_client, _db, _collection
    try:
        if AsyncIOMotorClient is None:
            _logger.info("observability_motor_skipped", reason="motor_not_installed")
            return
        uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = db_name or os.getenv("MONGO_DB", "chatbot_db")
        _mongo_client = AsyncIOMotorClient(uri)
        _db = _mongo_client[db_name]
        _collection = _db["llm_calls"]
        try:
            await _collection.create_index("request_id", unique=True)
            await _collection.create_index([("ts", -1)])
            await _collection.create_index([("user_id", 1), ("ts", -1)])
        except Exception:
            pass
        _logger.info("observability_motor_initialized")
    except Exception as e:
        _logger.warning("observability_motor_init_failed", error=str(e))

async def upsert_llm_call(request_id: str, update: Dict[str, Any]):
    # Avoid truthiness check; PyMongo/Motor collections forbid __bool__.
    if _collection is None:
        return
    try:
        await _collection.update_one({"request_id": request_id}, {"$set": update}, upsert=True)
    except Exception as e:
        _logger.warning("llm_call_upsert_failed", error=str(e))

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

class InstrumentationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        if OBS_DISABLED or request.method == "HEAD" or request.url.path in HEALTH_PATHS:
            return await call_next(request)
        start = time.time()
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        _current_request_id.set(request_id)
        user_id = request.headers.get("x-user-id") or "anon"
        session_id = request.headers.get("x-session-id")
        raw_body: bytes = b""
        try:
            raw_body = await request.body()
        except Exception:
            pass
        body_excerpt = raw_body.decode("utf-8", errors="ignore")[:200]
        redacted = body_excerpt if LOG_RAW else f"hash:{hash_text(body_excerpt)}"
        base_doc = {
            "request_id": request_id,
            "ts": start,
            "user_id": user_id,
            "session_id": session_id,
            "prompt_length_chars": len(body_excerpt),
            "prompt_token_estimate": len(body_excerpt) // 4,
            "routing_reason": None,
            "model_selected": None,
            "intent": None,
            "success": None,
            "error": None,
            "used_memory_ids": [],
            "cost_estimate": None,
        }
        await upsert_llm_call(request_id, base_doc)
        try:
            LLM_ACTIVE_REQUESTS.inc()
        except Exception:
            pass
        try:
            response = await call_next(request)
            success = 200 <= response.status_code < 400
            total_latency_ms = int((time.time() - start) * 1000)
            await upsert_llm_call(request_id, {"success": success, "total_latency_ms": total_latency_ms, "response_status": response.status_code, "redacted_body": redacted})
            _logger.info("llm_request_complete", request_id=request_id, latency_ms=total_latency_ms, status=response.status_code)
            response.headers["X-Request-ID"] = request_id
            try:
                observe_request(route=request.url.path, model=None, success=success, latency_seconds=total_latency_ms/1000.0, prompt_tokens=base_doc.get("prompt_token_estimate"))
            except Exception:
                pass
            return response
        except Exception as e:
            total_latency_ms = int((time.time() - start) * 1000)
            await upsert_llm_call(request_id, {"success": False, "error": str(e), "total_latency_ms": total_latency_ms})
            _logger.error("llm_request_error", request_id=request_id, error=str(e))
            try:
                observe_request(route=request.url.path, model=None, success=False, latency_seconds=total_latency_ms/1000.0, prompt_tokens=base_doc.get("prompt_token_estimate"))
            except Exception:
                pass
            # Re-raise to let FastAPI error handlers work.
            raise
        finally:
            try:
                LLM_ACTIVE_REQUESTS.dec()
            except Exception:
                pass

def register_instrumentation(app):
    # Schedule async init on startup
    @app.on_event("startup")
    async def _obs_init():  # type: ignore
        await init_motor()
    app.middleware("http")(InstrumentationMiddleware(app))

def get_current_request_id() -> str | None:
    try:
        return _current_request_id.get()
    except Exception:
        return None

async def update_llm_call(update: Dict[str, Any]):
    """Convenience helper to update current request's llm_call doc."""
    rid = get_current_request_id()
    if not rid:
        return
    await upsert_llm_call(rid, update)

__all__ = [
    "register_instrumentation",
    "get_current_request_id",
    "update_llm_call",
]
