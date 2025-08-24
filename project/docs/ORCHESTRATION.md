# Orchestration & Resilience Architecture

This document explains the multi-model orchestration, routing, and resilience capabilities introduced in v1.2.0.

## Goals
- Dynamic model selection based on intent, capability, latency, quality, and cost.
- Graceful degradation via ordered fallback chain.
- Transparent observability (structured logs, future metrics/alerts).
- Deterministic, auditable decision path.

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| Model Registry | `backend/config/model_registry.yml` | Declarative model metadata (capabilities, weights, fallback) |
| Intent Classifier | `backend/routing/intent_classifier.py` | Lightweight rule-based intent detection |
| Model Router | `backend/routing/model_router.py` | Scores eligible models (capability + heuristic weights) |
| Orchestrator | `backend/orchestration/llm_orchestrator.py` | Executes primary call, handles fallback & logging |
| Token Estimator | `backend/utils/token_estimator.py` | Cheap length heuristic for budgeting/trimming |
| Instrumentation | `backend/utils/instrumentation_middleware.py` | Request-scoped IDs, timing hooks |

## Flow
1. User query arrives with session/user identifiers.
2. Intent classifier tags request (e.g. `code`, `reasoning`, `chat`).
3. Router loads registry, filters models supporting required intents/capabilities.
4. Each candidate scored: `capability_match + latency_weight + quality_weight - cost_penalty` (simplified).
5. Highest score selected; orchestrator invokes provider client.
6. Errors / circuit-breaker opens → orchestrator walks fallback chain.
7. Structured log emitted with: `request_id`, `intent`, `selected_model`, `attempts`, `latency_ms`, `fallback_used`.

## Circuit Breaker (Concept)
- Tracks rolling failure ratio & consecutive errors.
- States: CLOSED → OPEN (skip calls) → HALF_OPEN (probe) → CLOSED.
- Prevents cascading latency or quota waste.

## Admin & Introspection (Planned)
- Reload registry
- List model health & breaker state
- Recent LLM call summaries
- Force model disable / enable

## Metrics (Planned Prometheus Names)
| Metric | Type | Description |
|--------|------|-------------|
| `llm_requests_total` | Counter | Total LLM invocation attempts |
| `llm_request_latency_seconds` | Histogram | End-to-end latency per model |
| `llm_fallback_total` | Counter | Count of fallback activations |
| `llm_tokens_prompt_total` | Counter | Accumulated prompt tokens (estimated) |
| `llm_tokens_completion_total` | Counter | Accumulated completion tokens |
| `llm_cost_usd_total` | Counter | Estimated spend |
| `circuit_open_gauge` | Gauge | Open breakers per model |

## Extending
- Add a new model: update registry with `id`, `provider`, `capabilities`, `weights`.
- Add an intent: extend rules in `intent_classifier.py` and update capabilities.
- Swap scoring: modify weight math in `model_router.py` (unit tests recommended).
- Add semantic intent: integrate embedding similarity pre-pass.

## Testing
See `backend/test_intent_and_orchestrator.py` for baseline cases (intent detection, fallback invocation).

## Roadmap
- Adaptive weight tuning (observed latency & quality feedback).
- Semantic + rule hybrid intent detection.
- Persistent metrics & Grafana dashboard JSON export.
- Structured decision trace object returned optionally for debugging.

---
Designed for clarity, resilience, and low operational overhead.
