"""
Health Checks for Kuro AI.

Provides liveness, readiness, and startup probes for Kubernetes/container orchestration.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status

# Import metrics if available
try:
    from .metrics import LLM_ACTIVE_REQUESTS
except Exception:
    LLM_ACTIVE_REQUESTS = None


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_fn: Callable[[], Awaitable[HealthCheckResult]]
    critical: bool = True  # If False, failure doesn't affect overall readiness
    timeout_seconds: float = 5.0


class HealthCheckRegistry:
    """Registry for health checks."""

    def __init__(self):
        self._checks: List[HealthCheck] = []
        self._liveness_checks: List[HealthCheck] = []
        self._readiness_checks: List[HealthCheck] = []
        self._startup_checks: List[HealthCheck] = []

    def register(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[HealthCheckResult]],
        critical: bool = True,
        timeout_seconds: float = 5.0,
        probe_types: Optional[List[str]] = None,
    ) -> None:
        """Register a health check."""
        probe_types = probe_types or ["readiness"]
        check = HealthCheck(
            name=name,
            check_fn=check_fn,
            critical=critical,
            timeout_seconds=timeout_seconds,
        )
        self._checks.append(check)

        if "liveness" in probe_types:
            self._liveness_checks.append(check)
        if "readiness" in probe_types:
            self._readiness_checks.append(check)
        if "startup" in probe_types:
            self._startup_checks.append(check)

    def get_checks(self, probe_type: str) -> List[HealthCheck]:
        """Get checks for a probe type."""
        if probe_type == "liveness":
            return self._liveness_checks
        elif probe_type == "readiness":
            return self._readiness_checks
        elif probe_type == "startup":
            return self._startup_checks
        return self._checks


# Global registry
_health_registry = HealthCheckRegistry()


def get_health_registry() -> HealthCheckRegistry:
    return _health_registry


async def run_checks(
    checks: List[HealthCheck],
    overall_critical_only: bool = False,
) -> Dict[str, Any]:
    """Run a set of health checks."""
    results = []
    overall_status = HealthStatus.HEALTHY
    start_time = time.time()

    for check in checks:
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                check.check_fn(),
                timeout=check.timeout_seconds,
            )
        except asyncio.TimeoutError:
            result = HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Timeout after {check.timeout_seconds}s",
                latency_ms=check.timeout_seconds * 1000,
            )
        except Exception as e:
            result = HealthCheckResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {e}",
            )

        results.append(result)

        # Determine overall status
        if check.critical or not overall_critical_only:
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

    return {
        "status": overall_status.value,
        "checks": [
            {
                "name": r.name,
                "status": r.status.value,
                "message": r.message,
                "details": r.details,
                "latency_ms": r.latency_ms,
                "timestamp": r.timestamp,
            }
            for r in results
        ],
        "total_latency_ms": (time.time() - start_time) * 1000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# BUILT-IN HEALTH CHECKS
# =============================================================================

async def check_basic_health() -> HealthCheckResult:
    """Basic liveness check - always returns healthy if process is running."""
    return HealthCheckResult(
        name="basic",
        status=HealthStatus.HEALTHY,
        message="Process is running",
        details={"pid": os.getpid()},
    )


async def check_memory_usage() -> HealthCheckResult:
    """Check memory usage."""
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()

        status = HealthStatus.HEALTHY
        if mem_percent > 90:
            status = HealthStatus.UNHEALTHY
        elif mem_percent > 75:
            status = HealthStatus.DEGRADED

        return HealthCheckResult(
            name="memory",
            status=status,
            message=f"Memory usage: {mem_percent:.1f}%",
            details={
                "rss_mb": mem_info.rss / 1024 / 1024,
                "vms_mb": mem_info.vms / 1024 / 1024,
                "percent": mem_percent,
            },
        )
    except ImportError:
        return HealthCheckResult(
            name="memory",
            status=HealthStatus.HEALTHY,
            message="psutil not available",
        )
    except Exception as e:
        return HealthCheckResult(
            name="memory",
            status=HealthStatus.UNHEALTHY,
            message=f"Memory check failed: {e}",
        )


async def check_disk_space() -> HealthCheckResult:
    """Check disk space."""
    try:
        import psutil
        disk = psutil.disk_usage("/")
        percent_used = (disk.used / disk.total) * 100

        status = HealthStatus.HEALTHY
        if percent_used > 95:
            status = HealthStatus.UNHEALTHY
        elif percent_used > 85:
            status = HealthStatus.DEGRADED

        return HealthCheckResult(
            name="disk",
            status=status,
            message=f"Disk usage: {percent_used:.1f}%",
            details={
                "total_gb": disk.total / 1024 / 1024 / 1024,
                "used_gb": disk.used / 1024 / 1024 / 1024,
                "free_gb": disk.free / 1024 / 1024 / 1024,
                "percent_used": percent_used,
            },
        )
    except ImportError:
        return HealthCheckResult(
            name="disk",
            status=HealthStatus.HEALTHY,
            message="psutil not available",
        )
    except Exception as e:
        return HealthCheckResult(
            name="disk",
            status=HealthStatus.UNHEALTHY,
            message=f"Disk check failed: {e}",
        )


async def check_mongodb() -> HealthCheckResult:
    """Check MongoDB connectivity."""
    start = time.time()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        latency_ms = (time.time() - start) * 1000

        return HealthCheckResult(
            name="mongodb",
            status=HealthStatus.HEALTHY,
            message="MongoDB connection successful",
            details={"latency_ms": latency_ms},
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="mongodb",
            status=HealthStatus.UNHEALTHY,
            message=f"MongoDB connection failed: {e}",
            latency_ms=latency_ms,
        )


async def check_pinecone() -> HealthCheckResult:
    """Check Pinecone connectivity."""
    start = time.time()
    try:
        from pinecone import Pinecone
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            return HealthCheckResult(
                name="pinecone",
                status=HealthStatus.UNHEALTHY,
                message="PINECONE_API_KEY not set",
                latency_ms=(time.time() - start) * 1000,
            )

        pc = Pinecone(api_key=api_key)
        # List indexes as connectivity test
        indexes = pc.list_indexes()
        latency_ms = (time.time() - start) * 1000

        return HealthCheckResult(
            name="pinecone",
            status=HealthStatus.HEALTHY,
            message="Pinecone connection successful",
            details={"indexes": [i.name for i in indexes], "latency_ms": latency_ms},
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="pinecone",
            status=HealthStatus.UNHEALTHY,
            message=f"Pinecone connection failed: {e}",
            latency_ms=latency_ms,
        )


async def check_redis() -> HealthCheckResult:
    """Check Redis connectivity."""
    start = time.time()
    try:
        import redis.asyncio as redis
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="REDIS_URL not set (optional)",
                latency_ms=(time.time() - start) * 1000,
            )

        client = redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
        await client.ping()
        await client.close()
        latency_ms = (time.time() - start) * 1000

        return HealthCheckResult(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful",
            details={"latency_ms": latency_ms},
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {e}",
            latency_ms=latency_ms,
        )


async def check_groq_api() -> HealthCheckResult:
    """Check Groq API connectivity."""
    start = time.time()
    try:
        import httpx
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return HealthCheckResult(
                name="groq",
                status=HealthStatus.UNHEALTHY,
                message="GROQ_API_KEY not set",
                latency_ms=(time.time() - start) * 1000,
            )

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            latency_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                return HealthCheckResult(
                    name="groq",
                    status=HealthStatus.HEALTHY,
                    message="Groq API accessible",
                    details={"latency_ms": latency_ms},
                    latency_ms=latency_ms,
                )
            elif response.status_code == 401:
                return HealthCheckResult(
                    name="groq",
                    status=HealthStatus.UNHEALTHY,
                    message="Groq API authentication failed",
                    details={"status_code": response.status_code, "latency_ms": latency_ms},
                    latency_ms=latency_ms,
                )
            else:
                return HealthCheckResult(
                    name="groq",
                    status=HealthStatus.DEGRADED,
                    message=f"Groq API returned {response.status_code}",
                    details={"status_code": response.status_code, "latency_ms": latency_ms},
                    latency_ms=latency_ms,
                )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="groq",
            status=HealthStatus.UNHEALTHY,
            message=f"Groq API check failed: {e}",
            latency_ms=latency_ms,
        )


async def check_active_requests() -> HealthCheckResult:
    """Check if there are too many active requests."""
    if LLM_ACTIVE_REQUESTS is None:
        return HealthCheckResult(
            name="active_requests",
            status=HealthStatus.HEALTHY,
            message="Metrics not available",
        )

    try:
        # Get gauge value
        current = LLM_ACTIVE_REQUESTS._value.get()
        max_requests = int(os.getenv("MAX_ACTIVE_REQUESTS", "100"))

        status = HealthStatus.HEALTHY
        if current > max_requests:
            status = HealthStatus.UNHEALTHY
        elif current > max_requests * 0.8:
            status = HealthStatus.DEGRADED

        return HealthCheckResult(
            name="active_requests",
            status=status,
            message=f"Active requests: {current}/{max_requests}",
            details={"active": current, "max": max_requests, "utilization": current / max_requests},
        )
    except Exception as e:
        return HealthCheckResult(
            name="active_requests",
            status=HealthStatus.DEGRADED,
            message=f"Active requests check failed: {e}",
        )


# Register built-in checks
def register_default_checks():
    """Register default health checks."""
    registry = get_health_registry()

    # Liveness - minimal checks
    registry.register("basic", check_basic_health, critical=True, probe_types=["liveness", "startup"])

    # Readiness - comprehensive checks
    registry.register("memory", check_memory_usage, critical=False, probe_types=["readiness"])
    registry.register("disk", check_disk_space, critical=False, probe_types=["readiness"])
    registry.register("mongodb", check_mongodb, critical=True, probe_types=["readiness", "startup"])
    registry.register("pinecone", check_pinecone, critical=True, probe_types=["readiness", "startup"])
    registry.register("redis", check_redis, critical=False, probe_types=["readiness"])
    registry.register("groq", check_groq_api, critical=True, probe_types=["readiness", "startup"])
    registry.register("active_requests", check_active_requests, critical=False, probe_types=["readiness"])


# =============================================================================
# FASTAPI ROUTER
# =============================================================================

def create_health_router() -> APIRouter:
    """Create FastAPI router for health endpoints."""
    router = APIRouter(tags=["health"])

    @router.get("/healthz", summary="Liveness probe")
    async def liveness():
        """Kubernetes liveness probe - process is alive."""
        result = await run_checks(
            get_health_registry().get_checks("liveness"),
            overall_critical_only=True,
        )
        status_code = (
            status.HTTP_200_OK
            if result["status"] == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            content=__import__("json").dumps(result),
            media_type="application/json",
            status_code=status_code,
        )

    @router.get("/ready", summary="Readiness probe")
    async def readiness():
        """Kubernetes readiness probe - ready to serve traffic."""
        result = await run_checks(
            get_health_registry().get_checks("readiness"),
            overall_critical_only=False,
        )
        status_code = (
            status.HTTP_200_OK
            if result["status"] in ("healthy", "degraded")
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            content=__import__("json").dumps(result),
            media_type="application/json",
            status_code=status_code,
        )

    @router.get("/startup", summary="Startup probe")
    async def startup():
        """Kubernetes startup probe - initialization complete."""
        result = await run_checks(
            get_health_registry().get_checks("startup"),
            overall_critical_only=True,
        )
        status_code = (
            status.HTTP_200_OK
            if result["status"] == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            content=__import__("json").dumps(result),
            media_type="application/json",
            status_code=status_code,
        )

    @router.get("/health", summary="Full health check")
    async def full_health():
        """Comprehensive health check with all details."""
        result = await run_checks(
            get_health_registry()._checks,
            overall_critical_only=False,
        )
        status_code = (
            status.HTTP_200_OK
            if result["status"] in ("healthy", "degraded")
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            content=__import__("json").dumps(result),
            media_type="application/json",
            status_code=status_code,
        )

    return router


__all__ = [
    "HealthStatus",
    "HealthCheckResult",
    "HealthCheck",
    "HealthCheckRegistry",
    "get_health_registry",
    "run_checks",
    "check_basic_health",
    "check_memory_usage",
    "check_disk_space",
    "check_mongodb",
    "check_pinecone",
    "check_redis",
    "check_groq_api",
    "check_active_requests",
    "register_default_checks",
    "create_health_router",
]