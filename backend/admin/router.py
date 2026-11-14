"""Admin router (Steps 6 & 7 initial) with protected endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Depends
from security.auth import require_admin
from config.config_loader import reload_registry
from reliability.circuit_breaker import stats as cb_stats
from observability.instrumentation_middleware import _collection as llm_collection  # type: ignore

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

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
    limit = max(1, min(limit, 100))
    if not llm_collection:
        return {"items": []}
    items = []
    try:
        async for doc in llm_collection.find({}).sort("ts", -1).limit(limit):  # type: ignore
            items.append({
                "ts": doc.get("ts"),
                "model": doc.get("model"),
                "success": doc.get("success"),
                "latency_ms": doc.get("total_latency_ms"),
                "response_status": doc.get("response_status"),
            })
    except Exception:
        pass
    return {"items": items}

@router.get("/raise-test-error")
async def raise_error():
    raise RuntimeError("Test error for alerting")

__all__ = ["router"]
