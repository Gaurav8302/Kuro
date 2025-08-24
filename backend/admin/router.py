"""Admin router (Steps 6 & 7 initial) with protected endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Depends
from admin.auth import verify_admin
from config.config_loader import reload_registry
from reliability.circuit_breaker import stats as cb_stats
from observability.instrumentation_middleware import _collection as llm_collection  # type: ignore

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(verify_admin)])

@router.get("/health")
async def admin_health():
    return {"status": "ok"}

@router.post("/reload-registry")
async def reload():
    data = reload_registry()
    return {"reloaded": True, "models": len(data.get('models', []))}

@router.get("/circuit-breakers")
async def circuit_breaker_stats():
    return cb_stats()

@router.get("/llm-calls")
async def list_llm_calls(limit: int = 5):
    if not llm_collection:
        return {"items": []}
    items = []
    try:
        async for doc in llm_collection.find({}).sort("ts", -1).limit(limit):  # type: ignore
            doc.pop("_id", None)
            items.append(doc)
    except Exception:
        pass
    return {"items": items}

@router.get("/raise-test-error")
async def raise_error():
    raise RuntimeError("Test error for alerting")

__all__ = ["router"]
