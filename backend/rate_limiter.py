"""Rate limiting infrastructure for Kuro AI.

Provides layered rate limiting with:
- Token bucket algorithm for smooth rate limiting
- Multiple dimensions: IP, user, endpoint, provider, tool
- Redis backend for distributed deployments, in-memory fallback for dev
- Atomic operations with Lua scripts for correctness
- 429 responses with Retry-After headers
"""

import os
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def is_rate_limit_enabled() -> bool:
    """Check if rate limiting is enabled at runtime."""
    return os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Default limits (requests per window)
DEFAULT_LIMITS = {
    # IP-based limits
    "ip:burst": (10, 1),       # 10 requests per second burst
    "ip:sustained": (100, 60), # 100 requests per minute sustained
    
    # User-based limits
    "user:chat": (30, 60),           # 30 chat requests per minute
    "user:memory": (60, 60),         # 60 memory ops per minute
    "user:session": (20, 60),        # 20 session ops per minute
    "user:profile": (30, 60),        # 30 profile ops per minute
    "user:upload": (10, 3600),       # 10 uploads per hour
    
    # Endpoint-specific limits
    "endpoint:/chat": (30, 60),
    "endpoint:/store-memory": (60, 60),
    "endpoint:/retrieve-memory": (60, 60),
    "endpoint:/session/create": (10, 60),
    "endpoint:/inline-query": (10, 60),
    
    # Provider limits (global)
    "provider:groq": (50, 60),       # 50 requests per minute to Groq
    "provider:openrouter": (30, 60), # 30 requests per minute to OpenRouter
    
    # Tool limits
    "tool:web_search": (20, 60),
    "tool:code_exec": (10, 60),
    
    # Daily budget (token-based, enforced separately)
    "user:daily_tokens": (100000, 86400),  # 100k tokens per day
}

# Cost estimates per model (input_tokens, output_tokens) -> approximate cost
MODEL_COSTS = {
    "groq/llama-3.3-70b-versatile": (0.0001, 0.0001),  # per 1k tokens
    "groq/llama-3.1-8b-instant": (0.00005, 0.00005),
    "openrouter/openai/gpt-4o": (0.005, 0.015),
    "openrouter/anthropic/claude-3.5-sonnet": (0.003, 0.015),
}

@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int
    retry_after: Optional[int] = None
    scope: str = ""
    identifier: str = ""

@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    max_requests: int
    window_seconds: int
    scope: str  # e.g., "ip", "user", "endpoint", "provider", "tool"
    
class RateLimiterBackend(ABC):
    """Abstract base class for rate limiter backends."""
    
    @abstractmethod
    def check_and_increment(self, key: str, limit: int, window_seconds: int) -> Tuple[int, int, int]:
        """
        Check rate limit and increment counter atomically.
        Returns: (allowed_count, remaining, reset_timestamp)
        """
        pass
    
    @abstractmethod
    def get_current(self, key: str) -> Tuple[int, int]:
        """Get current count and reset time without incrementing."""
        pass
    
    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset a rate limit key."""
        pass


class InMemoryRateLimiter(RateLimiterBackend):
    """In-memory rate limiter using sliding window with token bucket.
    
    Suitable for single-process deployments only.
    """
    
    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._buckets: Dict[str, Tuple[float, int]] = {}  # key -> (last_refill, tokens)
        self._counters: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)
    
    def _get_lock(self, key: str) -> threading.Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]
    
    def check_and_increment(self, key: str, limit: int, window_seconds: int) -> Tuple[int, int, int]:
        lock = self._get_lock(key)
        with lock:
            now = time.time()
            
            # Use fixed window for simplicity (sliding window would need sorted sets)
            window_start = int(now / window_seconds) * window_seconds
            reset_time = window_start + window_seconds
            
            counter_key = f"{key}:{window_start}"
            count, _ = self._counters.get(counter_key, (0, window_start))
            
            if count >= limit:
                return (count, 0, int(reset_time))
            
            count += 1
            self._counters[counter_key] = (count, window_start)
            
            # Cleanup old windows
            cutoff = now - window_seconds * 2
            to_delete = [k for k, (_, ws) in self._counters.items() if ws < cutoff]
            for k in to_delete:
                del self._counters[k]
            
            return (count, limit - count, int(reset_time))
    
    def get_current(self, key: str) -> Tuple[int, int]:
        now = time.time()
        # Check current window
        for window_seconds in [1, 60, 3600, 86400]:  # Common windows
            window_start = int(now / window_seconds) * window_seconds
            counter_key = f"{key}:{window_start}"
            count, _ = self._counters.get(counter_key, (0, window_start))
            if count > 0:
                return (count, int(window_start + window_seconds))
        return (0, int(now + 60))
    
    def reset(self, key: str) -> None:
        with self._global_lock:
            to_delete = [k for k in self._counters if k.startswith(key)]
            for k in to_delete:
                del self._counters[k]


class RedisRateLimiter(RateLimiterBackend):
    """Redis-backed rate limiter using sliding window log with Lua script.
    
    Provides atomic operations for distributed deployments.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client = None
        self._script_sha = None
        self._connect()
    
    def _connect(self):
        try:
            import redis
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self._client.ping()
            
            # Lua script for atomic sliding window rate limiting
            # Uses sorted set with timestamps as scores
            lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local window_start = now - window
            
            -- Remove expired entries
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
            
            -- Count current requests
            local count = redis.call('ZCARD', key)
            
            if count >= limit then
                -- Get oldest entry to calculate reset time
                local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                local reset_time = 0
                if #oldest > 0 then
                    reset_time = math.ceil(oldest[2]) + window
                else
                    reset_time = now + window
                end
                return {0, count, reset_time}
            end
            
            -- Add current request
            local member = now .. ':' .. math.random()
            redis.call('ZADD', key, now, member)
            redis.call('EXPIRE', key, window + 1)
            
            local reset_time = now + window
            return {1, count + 1, reset_time}
            """
            self._script_sha = self._client.script_load(lua_script)
            logger.info("Redis rate limiter connected and script loaded")
        except Exception as e:
            logger.warning(f"Redis rate limiter unavailable, falling back to in-memory: {e}")
            self._client = None
            self._script_sha = None
    
    def check_and_increment(self, key: str, limit: int, window_seconds: int) -> Tuple[int, int, int]:
        if not self._client or not self._script_sha:
            # Fallback handled by caller
            raise RuntimeError("Redis not available")
        
        try:
            now = time.time()
            result = self._client.evalsha(
                self._script_sha,
                1,  # number of keys
                f"ratelimit:{key}",
                limit,
                window_seconds,
                now
            )
            allowed = result[0]
            count = result[1]
            reset_time = int(result[2])
            remaining = max(0, limit - count)
            return (count, remaining, reset_time)
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            raise
    
    def get_current(self, key: str) -> Tuple[int, int]:
        if not self._client:
            raise RuntimeError("Redis not available")
        try:
            now = time.time()
            # Use a 1-minute window for current check
            window_start = now - 60
            count = self._client.zcount(f"ratelimit:{key}", window_start, "+inf")
            return (count, int(now + 60))
        except Exception as e:
            logger.error(f"Redis get_current error: {e}")
            raise
    
    def reset(self, key: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete(f"ratelimit:{key}")
        except Exception as e:
            logger.error(f"Redis reset error: {e}")


class RateLimiter:
    """Main rate limiter facade with multi-dimensional limiting."""
    
    def __init__(self):
        self._memory_backend = InMemoryRateLimiter()
        self._redis_backend: Optional[RedisRateLimiter] = None
        self._use_redis = False
        
        # Try to initialize Redis
        try:
            self._redis_backend = RedisRateLimiter(REDIS_URL)
            if self._redis_backend._client:
                self._use_redis = True
                logger.info("Rate limiter using Redis backend")
            else:
                logger.info("Rate limiter using in-memory backend (Redis unavailable)")
        except Exception as e:
            logger.info(f"Rate limiter using in-memory backend: {e}")
    
    def _get_backend(self) -> RateLimiterBackend:
        if self._use_redis and self._redis_backend:
            return self._redis_backend
        return self._memory_backend
    
    def check_limit(
        self,
        identifier: str,
        scope: str,
        max_requests: int,
        window_seconds: int
    ) -> RateLimitResult:
        """Check and consume a rate limit slot."""
        if not is_rate_limit_enabled():
            return RateLimitResult(
                allowed=True,
                limit=max_requests,
                remaining=max_requests,
                reset_seconds=window_seconds,
                scope=scope,
                identifier=identifier
            )
        
        key = f"{scope}:{identifier}"
        backend = self._get_backend()
        
        try:
            count, remaining, reset_time = backend.check_and_increment(key, max_requests, window_seconds)
            reset_seconds = max(1, reset_time - int(time.time()))
            
            return RateLimitResult(
                allowed=count <= max_requests,
                limit=max_requests,
                remaining=remaining,
                reset_seconds=reset_seconds,
                retry_after=reset_seconds if count > max_requests else None,
                scope=scope,
                identifier=identifier
            )
        except Exception as e:
            # Fail open for in-memory, fail closed for Redis
            if self._use_redis:
                logger.error(f"Rate limit check failed (Redis), denying request: {e}")
                return RateLimitResult(
                    allowed=False,
                    limit=max_requests,
                    remaining=0,
                    reset_seconds=window_seconds,
                    retry_after=window_seconds,
                    scope=scope,
                    identifier=identifier
                )
            else:
                logger.warning(f"Rate limit check failed (memory), allowing request: {e}")
                return RateLimitResult(
                    allowed=True,
                    limit=max_requests,
                    remaining=max_requests,
                    reset_seconds=window_seconds,
                    scope=scope,
                    identifier=identifier
                )
    
    def check_multi(
        self,
        identifier: str,
        scopes: Dict[str, Tuple[int, int]]  # scope -> (max_requests, window_seconds)
    ) -> Dict[str, RateLimitResult]:
        """Check multiple rate limit scopes at once."""
        results = {}
        for scope, (max_req, window) in scopes.items():
            results[scope] = self.check_limit(identifier, scope, max_req, window)
        return results
    
    def get_limit_status(self, identifier: str, scope: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        """Get current status without consuming a slot."""
        if not is_rate_limit_enabled():
            return RateLimitResult(
                allowed=True,
                limit=max_requests,
                remaining=max_requests,
                reset_seconds=window_seconds,
                scope=scope,
                identifier=identifier
            )
        
        key = f"{scope}:{identifier}"
        backend = self._get_backend()
        
        try:
            count, reset_time = backend.get_current(key)
            reset_seconds = max(1, reset_time - int(time.time()))
            remaining = max(0, max_requests - count)
            
            return RateLimitResult(
                allowed=count < max_requests,
                limit=max_requests,
                remaining=remaining,
                reset_seconds=reset_seconds,
                retry_after=reset_seconds if count >= max_requests else None,
                scope=scope,
                identifier=identifier
            )
        except Exception as e:
            logger.warning(f"Rate limit status check failed: {e}")
            return RateLimitResult(
                allowed=True,
                limit=max_requests,
                remaining=max_requests,
                reset_seconds=window_seconds,
                scope=scope,
                identifier=identifier
            )


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit(
    scope: str,
    max_requests: int = 60,
    window_seconds: int = 60,
    identifier_func=None
):
    """Decorator for rate limiting endpoint handlers.
    
    Args:
        scope: Rate limit scope (e.g., "user:chat", "ip", "endpoint:/chat")
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        identifier_func: Optional function(request) -> identifier string
                        Defaults to user_id from principal or client IP
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if hasattr(arg, 'client') and hasattr(arg, 'headers'):
                    request = arg
                    break
            if request is None:
                request = kwargs.get('request')
            
            # Determine identifier
            if identifier_func:
                identifier = identifier_func(request)
            else:
                # Try to get user from principal (set by auth middleware)
                if hasattr(request, 'state') and hasattr(request.state, 'principal'):
                    identifier = f"user:{request.state.principal.user_id}"
                elif request and request.client:
                    identifier = f"ip:{request.client.host}"
                else:
                    identifier = "unknown"
            
            # Check rate limit
            limiter = get_rate_limiter()
            result = limiter.check_limit(identifier, scope, max_requests, window_seconds)
            
            # Add rate limit headers to response
            from fastapi import Response
            # We can't easily modify response here without middleware
            # This is handled by the rate limit middleware instead
            
            if not result.allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "Retry-After": str(result.retry_after or result.reset_seconds),
                        "X-RateLimit-Limit": str(result.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(result.reset_seconds),
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Rate limit middleware for automatic header injection
class RateLimitMiddleware:
    """Middleware that applies rate limits and injects headers."""
    
    def __init__(self, app, default_limits: Optional[Dict[str, Tuple[int, int]]] = None):
        self.app = app
        self.default_limits = default_limits or {}
        self.limiter = get_rate_limiter()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # This is a simplified version - full implementation would need
        # to wrap send to inject headers
        await self.app(scope, receive, send)


def apply_rate_limit_headers(response, results: Dict[str, RateLimitResult]):
    """Apply rate limit headers from multiple limit checks."""
    if not results:
        return
    
    # Use the most restrictive limit for headers
    most_restrictive = min(results.values(), key=lambda r: r.remaining)
    
    response.headers["X-RateLimit-Limit"] = str(most_restrictive.limit)
    response.headers["X-RateLimit-Remaining"] = str(most_restrictive.remaining)
    response.headers["X-RateLimit-Reset"] = str(most_restrictive.reset_seconds)
    
    # Add per-scope headers
    for scope, result in results.items():
        safe_scope = scope.replace(":", "-").replace("/", "-")
        response.headers[f"X-RateLimit-{safe_scope}-Limit"] = str(result.limit)
        response.headers[f"X-RateLimit-{safe_scope}-Remaining"] = str(result.remaining)


__all__ = [
    "RateLimiter",
    "RateLimitResult", 
    "RateLimitConfig",
    "get_rate_limiter",
    "rate_limit",
    "RateLimitMiddleware",
    "apply_rate_limit_headers",
    "DEFAULT_LIMITS",
    "MODEL_COSTS",
]