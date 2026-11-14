"""
Observability package for Kuro AI.

Provides structured logging, metrics, health checks, alerting,
and instrumentation for monitoring and debugging.
"""

from .logging import (
    JSONFormatter,
    StructuredLogger,
    get_logger,
    set_request_context,
    clear_request_context,
    get_request_id,
    get_user_id,
    get_session_id,
    get_trace_id,
    get_span_id,
    generate_request_id,
    generate_trace_id,
    generate_span_id,
    log_with_context,
    setup_logging,
    RequestContextMiddleware,
)

from .metrics import (
    observe_request,
    LLM_REQUESTS_TOTAL,
    LLM_REQUEST_LATENCY_SECONDS,
    LLM_PROMPT_TOKENS_TOTAL,
    LLM_COMPLETION_TOKENS_TOTAL,
    LLM_COST_USD_TOTAL,
    LLM_ACTIVE_REQUESTS,
)

from .monitoring import (
    observe_routing,
    snapshot,
)

from .instrumentation_middleware import (
    register_instrumentation,
    get_current_request_id,
    update_llm_call,
    init_motor,
    upsert_llm_call,
    hash_text,
    InstrumentationMiddleware,
)

from .health import (
    HealthStatus,
    HealthCheckResult,
    HealthCheck,
    HealthCheckRegistry,
    get_health_registry,
    run_checks,
    check_basic_health,
    check_memory_usage,
    check_disk_space,
    check_mongodb,
    check_pinecone,
    check_redis,
    check_groq_api,
    check_active_requests,
    register_default_checks,
    create_health_router,
)

from .alerting import (
    AlertSeverity,
    AlertStatus,
    Alert,
    AlertRule,
    NotificationChannel,
    LogNotificationChannel,
    WebhookNotificationChannel,
    EmailNotificationChannel,
    AlertManager,
    create_default_rules,
    get_alert_manager,
    init_alerting,
    shutdown_alerting,
)

__all__ = [
    # logging
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
    # metrics
    "observe_request",
    "LLM_REQUESTS_TOTAL",
    "LLM_REQUEST_LATENCY_SECONDS",
    "LLM_PROMPT_TOKENS_TOTAL",
    "LLM_COMPLETION_TOKENS_TOTAL",
    "LLM_COST_USD_TOTAL",
    "LLM_ACTIVE_REQUESTS",
    # monitoring
    "observe_routing",
    "snapshot",
    # instrumentation
    "register_instrumentation",
    "get_current_request_id",
    "update_llm_call",
    "init_motor",
    "upsert_llm_call",
    "hash_text",
    "InstrumentationMiddleware",
    # health
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
    # alerting
    "AlertSeverity",
    "AlertStatus",
    "Alert",
    "AlertRule",
    "NotificationChannel",
    "LogNotificationChannel",
    "WebhookNotificationChannel",
    "EmailNotificationChannel",
    "AlertManager",
    "create_default_rules",
    "get_alert_manager",
    "init_alerting",
    "shutdown_alerting",
]