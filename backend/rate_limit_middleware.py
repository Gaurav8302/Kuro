"""Rate limit middleware for FastAPI integration.

Provides automatic rate limiting with configurable rules per endpoint/user/IP.
"""

import time
import logging
from typing import Callable, Dict, Optional, Tuple, List
from dataclasses import dataclass

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from rate_limiter import (
    get_rate_limiter,
    RateLimitResult,
    DEFAULT_LIMITS,
    apply_rate_limit_headers,
    is_rate_limit_enabled,
)

logger = logging.getLogger(__name__)

# Endpoint-specific limit configurations
ENDPOINT_LIMITS = {
    "/chat": [("user:chat", 30, 60), ("endpoint:/chat", 30, 60), ("ip:sustained", 100, 60)],
    "/store-memory": [("user:memory", 60, 60), ("endpoint:/store-memory", 60, 60), ("ip:sustained", 100, 60)],
    "/retrieve-memory": [("user:memory", 60, 60), ("endpoint:/retrieve-memory", 60, 60), ("ip:sustained", 100, 60)],
    "/session/create": [("user:session", 20, 60), ("endpoint:/session/create", 10, 60), ("ip:sustained", 100, 60)],
    "/inline-query": [("user:chat", 10, 60), ("endpoint:/inline-query", 10, 60), ("ip:sustained", 100, 60)],
    "/user/": [("user:profile", 30, 60), ("ip:sustained", 100, 60)],  # prefix match
    "/sessions/": [("user:session", 30, 60), ("ip:sustained", 100, 60)],
    "/chat/": [("user:session", 30, 60), ("ip:sustained", 100, 60)],  # chat history
    "/history/": [("user:session", 30, 60), ("ip:sustained", 100, 60)],
    "/session/": [("user:session", 20, 60), ("ip:sustained", 100, 60)],  # PUT/DELETE session
    "/metrics": [("ip:burst", 10, 1), ("ip:sustained", 30, 60)],  # stricter for metrics
    "/health": [("ip:burst", 30, 1), ("ip:sustained", 200, 60)],
    "/live": [("ip:burst", 30, 1), ("ip:sustained", 200, 60)],
    "/ready": [("ip:burst", 30, 1), ("ip:sustained", 200, 60)],
    "/ping": [("ip:burst", 30, 1), ("ip:sustained", 200, 60)],
    "/api-status": [("ip:burst", 5, 1), ("ip:sustained", 10, 60)],
}

# Public endpoints that only get IP-based limits
PUBLIC_ENDPOINTS = {"/", "/healthz", "/live", "/ready", "/ping"}

# Admin endpoints get stricter limits
ADMIN_ENDPOINTS = {"/admin/"}


def match_endpoint(path: str, prefix_rules: Dict[str, List[Tuple[str, int, int]]]) -> List[Tuple[str, int, int]]:
    """Match a path to rate limit rules.
    
    Returns list of (scope, max_requests, window_seconds) tuples.
    """
    # Exact match first
    if path in prefix_rules:
        return prefix_rules[path]
    
    # Prefix match (for /user/, /sessions/, etc.)
    for prefix, rules in prefix_rules.items():
        if prefix.endswith("/") and path.startswith(prefix):
            return rules
    
    # Default to IP-based limits
    return [("ip:sustained", 100, 60)]


def get_identifier(request: Request, principal=None) -> Tuple[str, str]:
    """Get rate limit identifier from request.
    
    Returns (identifier, identifier_type) where type is 'user' or 'ip'.
    """
    # Try to get user from principal (set by auth dependency)
    if principal and hasattr(principal, 'user_id'):
        return f"user:{principal.user_id}", "user"
    
    # Fall back to IP
    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_host = forwarded_for.split(",")[0].strip()
    return f"ip:{client_host}", "ip"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic rate limiting."""
    
    def __init__(
        self,
        app,
        endpoint_limits: Optional[Dict[str, List[Tuple[str, int, int]]]] = None,
        public_endpoints: Optional[set] = None,
        admin_endpoints: Optional[set] = None,
        exempt_paths: Optional[set] = None,
    ):
        super().__init__(app)
        self.endpoint_limits = endpoint_limits or ENDPOINT_LIMITS
        self.public_endpoints = public_endpoints or PUBLIC_ENDPOINTS
        self.admin_endpoints = admin_endpoints or ADMIN_ENDPOINTS
        self.exempt_paths = exempt_paths or {"/docs", "/redoc", "/openapi.json", "/favicon.ico"}
        self.limiter = get_rate_limiter()
    
    def _is_exempt(self, path: str) -> bool:
        return path in self.exempt_paths or any(path.startswith(p) for p in self.exempt_paths if p.endswith("/"))
    
    def _is_public(self, path: str) -> bool:
        return path in self.public_endpoints or any(path.startswith(p) for p in self.public_endpoints if p.endswith("/"))
    
    def _is_admin(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.admin_endpoints)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        # Skip if rate limiting is disabled
        if not is_rate_limit_enabled():
            return await call_next(request)
        
        # Skip exempt paths
        if self._is_exempt(path):
            return await call_next(request)
        
        # Get principal from request state (set by auth dependency)
        principal = getattr(request.state, "principal", None)
        
        # Get identifier
        identifier, id_type = get_identifier(request, principal)
        
        # Determine applicable limits
        if self._is_admin(path):
            # Admin endpoints get stricter limits
            limits = [("user:admin", 10, 60), ("ip:sustained", 20, 60)]
        elif self._is_public(path):
            # Public endpoints only get IP limits
            limits = [("ip:burst", 30, 1), ("ip:sustained", 200, 60)]
        else:
            # Protected endpoints get matched limits
            limits = match_endpoint(path, self.endpoint_limits)
            
            # For user-specific scopes, use user identifier
            # For IP scopes, use IP identifier
            matched_limits = []
            for scope, max_req, window in limits:
                if scope.startswith("user:") and id_type == "user":
                    matched_limits.append((scope, max_req, window, identifier))
                elif scope.startswith("ip:") and id_type == "ip":
                    matched_limits.append((scope, max_req, window, identifier))
                elif scope.startswith("endpoint:"):
                    # Endpoint limits apply to all users on that endpoint
                    matched_limits.append((scope, max_req, window, f"endpoint:{path}"))
                else:
                    matched_limits.append((scope, max_req, window, identifier))
            # Convert to the format expected below: (scope, max_req, window, identifier)
            limits = matched_limits
        
        # Check all applicable limits
        results = {}
        for scope, max_req, window, limit_identifier in limits:
            result = self.limiter.check_limit(limit_identifier, scope, max_req, window)
            results[scope] = result
            
            if not result.allowed:
                # Rate limit exceeded
                logger.warning(
                    f"Rate limit exceeded: {scope} for {limit_identifier} "
                    f"({result.limit}/{window}s)"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please slow down.",
                        "scope": scope,
                        "retry_after": result.retry_after,
                    },
                    headers={
                        "Retry-After": str(result.retry_after or result.reset_seconds),
                        "X-RateLimit-Limit": str(result.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(result.reset_seconds),
                    }
                )
        
        # All limits passed - proceed with request
        response = await call_next(request)
        
        # Add rate limit headers
        apply_rate_limit_headers(response, results)
        
        return response


def create_rate_limit_middleware(app, **kwargs) -> RateLimitMiddleware:
    """Factory function to create and register rate limit middleware."""
    middleware = RateLimitMiddleware(app, **kwargs)
    app.add_middleware(RateLimitMiddleware, **kwargs)
    return middleware


__all__ = [
    "RateLimitMiddleware",
    "create_rate_limit_middleware",
    "ENDPOINT_LIMITS",
    "PUBLIC_ENDPOINTS",
    "ADMIN_ENDPOINTS",
    "match_endpoint",
    "get_identifier",
]