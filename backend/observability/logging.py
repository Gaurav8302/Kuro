"""
Structured Logging for Kuro AI.

Provides JSON-structured logging with correlation IDs, request context,
and consistent field names for log aggregation.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from functools import wraps


# Context variables for correlation
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON log formatter with consistent fields."""

    def __init__(self, service_name: str = "kuro-ai", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Add correlation IDs
        request_id = _request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        user_id = _user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id

        session_id = _session_id_var.get()
        if session_id:
            log_entry["session_id"] = session_id

        trace_id = _trace_id_var.get()
        if trace_id:
            log_entry["trace_id"] = trace_id

        span_id = _span_id_var.get()
        if span_id:
            log_entry["span_id"] = span_id

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "thread", "threadName",
                "exc_info", "exc_text", "stack_info", "getMessage"
            }:
                # Sanitize value for JSON
                try:
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class StructuredLogger:
    """Wrapper for structured logging with context."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs):
        """Log with extra fields."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        self._log(logging.ERROR, message, exc_info=True, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> None:
    """Set request context for logging."""
    if request_id:
        _request_id_var.set(request_id)
    if user_id:
        _user_id_var.set(user_id)
    if session_id:
        _session_id_var.set(session_id)
    if trace_id:
        _trace_id_var.set(trace_id)
    if span_id:
        _span_id_var.set(span_id)


def clear_request_context() -> None:
    """Clear request context."""
    _request_id_var.set(None)
    _user_id_var.set(None)
    _session_id_var.set(None)
    _trace_id_var.set(None)
    _span_id_var.set(None)


def get_request_id() -> Optional[str]:
    return _request_id_var.get()


def get_user_id() -> Optional[str]:
    return _user_id_var.get()


def get_session_id() -> Optional[str]:
    return _session_id_var.get()


def get_trace_id() -> Optional[str]:
    return _trace_id_var.get()


def get_span_id() -> Optional[str]:
    return _span_id_var.get()


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def generate_trace_id() -> str:
    """Generate a new trace ID (W3C format)."""
    return uuid.uuid4().hex[:32]


def generate_span_id() -> str:
    """Generate a new span ID (W3C format)."""
    return uuid.uuid4().hex[:16]


def log_with_context(logger: StructuredLogger, level: int, message: str, **kwargs):
    """Log with automatic context injection."""
    # Auto-inject context
    request_id = get_request_id()
    user_id = get_user_id()
    session_id = get_session_id()
    trace_id = get_trace_id()
    span_id = get_span_id()

    if request_id:
        kwargs.setdefault("request_id", request_id)
    if user_id:
        kwargs.setdefault("user_id", user_id)
    if session_id:
        kwargs.setdefault("session_id", session_id)
    if trace_id:
        kwargs.setdefault("trace_id", trace_id)
    if span_id:
        kwargs.setdefault("span_id", span_id)

    logger._log(level, message, **kwargs)


def setup_logging(
    service_name: str = "kuro-ai",
    level: str = "INFO",
    json_format: bool = True,
) -> None:
    """Configure application-wide structured logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if json_format:
        handler.setFormatter(JSONFormatter(service_name=service_name))
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ))

    root_logger.addHandler(handler)

    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class RequestContextMiddleware:
    """Middleware to set request context for logging."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("headers", {}).get(b"x-request-id", generate_request_id()).decode()
        trace_id = scope.get("headers", {}).get(b"x-trace-id", generate_trace_id()).decode()
        span_id = generate_span_id()

        set_request_context(
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
        )

        # Add to response headers
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                headers.append((b"x-trace-id", trace_id.encode()))
                headers.append((b"x-span-id", span_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            clear_request_context()


__all__ = [
    "JSONFormatter",
    "StructuredLogger",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "get_request_id",
    "get_user_id",
    "get_session_id",
    "get_trace_id",
    "get_span_id",
    "generate_request_id",
    "generate_trace_id",
    "generate_span_id",
    "log_with_context",
    "setup_logging",
    "RequestContextMiddleware",
]