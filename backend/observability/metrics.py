"""Prometheus metrics setup (Step 2).

Exposes counters/histograms for LLM orchestration and general API performance.
"""
from __future__ import annotations
from prometheus_client import Counter, Histogram, Gauge

# Core LLM request lifecycle metrics
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM-related requests received",
    ["route", "model", "success"],
)

LLM_REQUEST_LATENCY_SECONDS = Histogram(
    "llm_request_latency_seconds",
    "Latency of LLM related requests in seconds",
    ["route", "model", "success"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

LLM_PROMPT_TOKENS_TOTAL = Counter(
    "llm_prompt_tokens_total",
    "Accumulated prompt tokens (estimated)",
    ["model"],
)

LLM_COMPLETION_TOKENS_TOTAL = Counter(
    "llm_completion_tokens_total",
    "Accumulated completion tokens (estimated)",
    ["model"],
)

LLM_COST_USD_TOTAL = Counter(
    "llm_cost_usd_total",
    "Accumulated estimated USD cost",
    ["model"],
)

LLM_ACTIVE_REQUESTS = Gauge(
    "llm_active_requests","Number of in-flight LLM requests"
)

def observe_request(route: str, model: str | None, success: bool, latency_seconds: float, prompt_tokens: int | None = None, completion_tokens: int | None = None, cost_usd: float | None = None):
    model_label = model or "unknown"
    success_label = "true" if success else "false"
    LLM_REQUESTS_TOTAL.labels(route=route, model=model_label, success=success_label).inc()
    LLM_REQUEST_LATENCY_SECONDS.labels(route=route, model=model_label, success=success_label).observe(latency_seconds)
    if prompt_tokens:
        LLM_PROMPT_TOKENS_TOTAL.labels(model=model_label).inc(prompt_tokens)
    if completion_tokens:
        LLM_COMPLETION_TOKENS_TOTAL.labels(model=model_label).inc(completion_tokens)
    if cost_usd:
        LLM_COST_USD_TOTAL.labels(model=model_label).inc(cost_usd)

__all__ = [
    "observe_request",
    "LLM_REQUESTS_TOTAL",
    "LLM_REQUEST_LATENCY_SECONDS",
    "LLM_PROMPT_TOKENS_TOTAL",
    "LLM_COMPLETION_TOKENS_TOTAL",
    "LLM_COST_USD_TOTAL",
    "LLM_ACTIVE_REQUESTS",
]
