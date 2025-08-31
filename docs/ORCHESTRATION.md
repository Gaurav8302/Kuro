# Kuro AI Orchestration and Multi-Model Routing

This document outlines the architecture of Kuro AI's backend orchestration layer, focusing on how it intelligently routes requests between multiple Large Language Models (LLMs) from different providers like Groq and OpenRouter.

## Core Components

The orchestration system is built around a few key modules working together:

1.  **`llm_orchestrator.py`**: The central nervous system. It receives the user's request and coordinates the entire process from intent classification to final response generation.
2.  **`intent_classifier.py`**: A fast, rule-based classifier that analyzes the user's message to determine their intent (e.g., `casual_chat`, `complex_reasoning`, `code_generation`).
3.  **`model_router_v2.py`**: The brain of the routing logic. It takes the user's query and classified intents and selects the optimal model for the task.
4.  **`model_registry.yml`**: A configuration file that acts as a catalog of all available models, detailing their capabilities, providers (Groq, OpenRouter), context windows, and other metadata.
5.  **`fallback_router.py` & `circuit_breaker.py`**: The reliability layer. This system manages failures by providing fallback model chains and preventing repeated calls to unavailable models.

## The Orchestration Flow

When a user sends a message, the following sequence of events occurs:

![Orchestration Flow](https://i.imgur.com/example.png)  <!-- Placeholder for a real diagram -->

1.  **Intent Classification**: The `llm_orchestrator` first passes the user message to the `intent_classifier`. This module uses regular expressions to quickly tag the message with one or more intents. For example, a message containing "summarize this long article" would be tagged with `long_context_summary`.

2.  **Model Selection (`model_router_v2`)**: The orchestrator then calls the `get_best_model` function from the V2 router. This router uses a sophisticated, multi-stage process to choose a model:
    *   **Cache Check**: It first checks an in-memory cache to see if a similar query was routed recently. If so, it returns the cached model choice instantly.
    *   **Rule-Based Routing**: It applies a set of high-confidence rules. For example, a rule might state that any query with the `code_generation` intent should immediately be routed to `gpt-4o` via OpenRouter.
    *   **LLM-as-Router (Future-Proofing)**: The architecture includes a stub for an LLM-based router. This could be enabled to use a small, fast model to make routing decisions for queries that don't fit simple rules.
    *   **Default & Sticky Sessions**: If no high-confidence rule matches, it falls back to a default model. It also leverages a "sticky session" feature, preferring to reuse the last successful model for a given user to maintain conversational consistency.

3.  **Execution and Fallback**:
    *   The `llm_orchestrator` attempts to execute the request using the chosen model via the appropriate client (Groq or OpenRouter).
    *   **Circuit Breaker**: Before making the call, it checks with the `circuit_breaker` to ensure the target model is currently healthy. If the model has failed recently, the circuit breaker will trip, and the request will be immediately rerouted.
    *   **Fallback Chain**: If the API call fails (e.g., the provider's server returns an error), the orchestrator consults the `build_fallback_chain` function. This provides a predefined list of alternative models to try in sequence. For example, if `groq/llama3-70b` fails, the chain might specify trying `openrouter/claude-3-sonnet` next.
    *   This process repeats until a model successfully returns a response or all fallbacks are exhausted.

4.  **Response and Logging**: Once a response is generated, the orchestrator packages it with metadata (which model was used, whether fallbacks were triggered, latency, etc.) and returns it to the main application. It also logs this information for monitoring and analysis.

This multi-layered approach ensures that Kuro AI is not only intelligent but also fast, cost-effective, and highly reliable. It dynamically adapts to the user's needs and can withstand failures from individual model providers without interrupting the user experience.

---

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
