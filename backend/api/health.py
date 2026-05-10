"""
Health API Router — Health check endpoints

Provides /healthz, /ready, /live, /ping endpoints
extracted from the monolithic chatbot.py.
"""

from datetime import datetime
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/healthz")
async def healthz():
    """Lightweight health probe (no external calls)."""
    return {"status": "ok"}


@router.get("/live")
async def live():
    """Liveness probe for orchestrators."""
    return {"live": True}


@router.get("/ready")
async def ready():
    """Readiness probe — extend with dependency checks as needed."""
    return {"ready": True}


@router.get("/ping")
async def ping():
    """Auto-warm ping to prevent Render from sleeping."""
    return {
        "status": "ok",
        "message": "Server is awake and healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_check": "render_auto_warm",
    }
