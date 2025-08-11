### Orchestration & Monitoring Stack (Scaffold)

This directory now includes initial scaffolding for advanced model routing,
metrics, and reliability features. Steps roadmap (see user prompt for details):

0. Config & Registry (DONE)
1. Instrumentation middleware & Mongo logging (DONE basic)
2. Prometheus metrics (IN PROGRESS basic gauges/counters)
3. Circuit breaker & fallback routing (IN PROGRESS - basic CB + fallback list)
4. Model router & rules (IN PROGRESS - rule evaluator + selection)
5. Token estimation & trimming (IN PROGRESS - heuristic + trimming)
6. Admin endpoints & security (BASIC: API key, registry reload, CB stats, list llm calls)
7. Alerts & error tracking (BASIC: Sentry init hook)
8. Grafana dashboard spec (INITIAL OUTLINE below)
9. Tests & CI (PARTIAL: routing/resilience tests; need admin/metrics tests)
6. Admin endpoints & security (TODO)
7. Alerts & error tracking (TODO)
8. Grafana dashboard spec (TODO)
9. Tests & CI (PARTIAL baseline tests exist)
10. Deployment notes (ADD)

Environment variables of interest:
- MODEL_REGISTRY_PATH (overrides default registry file path)
- LOG_RAW_CONTENT (bool) controls raw content logging
- ADMIN_API_KEY for admin route protection (future)

Model registry file at `config/model_registry.yml`.

Next implementation step: add instrumentation middleware that writes to a new
`llm_calls` collection (Motor based) and attaches a request_id to each response.

### Grafana Dashboard Outline (Step 8 Draft)
- Panel: LLM Request Rate (llm_requests_total rate by model)
- Panel: LLM Error Rate (% success=false)
- Panel: P95 Latency (histogram_quantile over llm_request_latency_seconds_bucket)
- Panel: Active Requests (gauge)
- Panel: Circuit Breakers Open (table via /admin/circuit-breakers)
- Panel: Top Models Usage Split (pie of llm_requests_total by model)
- Panel: Token Consumption (prompt vs completion counters)
- Panel: Estimated Cost (llm_cost_usd_total over time)
