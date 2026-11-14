# Kuro AI - Production Hardening Checklist

## Infrastructure Security

### Network
- [ ] VPC with private subnets for backend services
- [ ] Public subnets only for load balancer/frontend
- [ ] Security groups: least privilege (backend only accepts from LB)
- [ ] Network ACLs for additional layer
- [ ] VPC Flow Logs enabled
- [ ] DDoS protection (AWS Shield / Cloudflare)
- [ ] WAF rules for API endpoints

### Container Security
- [ ] Non-root user in containers (UID 1000)
- [ ] Read-only root filesystem where possible
- [ ] Drop all capabilities, add only required
- [ ] No privileged containers
- [ ] Resource limits (CPU, memory) set
- [ ] Health checks configured
- [ ] Image scanning in CI/CD (Trivy)
- [ ] Base images updated regularly
- [ ] Multi-stage builds to minimize attack surface

### Secrets Management
- [ ] No secrets in code, config files, or Docker images
- [ ] Use secret manager (AWS Secrets Manager, HashiCorp Vault, Doppler)
- [ ] Secrets injected at runtime via environment variables
- [ ] Rotation schedule documented and automated
- [ ] Audit logging for secret access
- [ ] Separate secrets per environment (dev/staging/prod)

### TLS/SSL
- [ ] TLS 1.2+ enforced everywhere
- [ ] Valid certificates (Let's Encrypt or managed certs)
- [ ] HSTS header enabled
- [ ] Certificate transparency monitoring
- [ ] mTLS for service-to-service (optional)

## Application Security

### Authentication & Authorization
- [ ] Clerk JWT validation with JWKS rotation
- [ ] RS256 algorithm only
- [ ] Issuer, audience, expiration validated
- [ ] Token revocation checking (if available)
- [ ] Admin endpoints protected by allowlist
- [ ] Metrics endpoint protected by bearer token
- [ ] No caller-supplied user_id trusted

### Input Validation
- [ ] Pydantic models for all request bodies
- [ ] Strict JSON Schema validation
- [ ] File upload validation (type, size, magic bytes)
- [ ] Prompt injection detection
- [ ] Output guardrails (secret detection, hallucination check)
- [ ] SSRF protection for outbound requests

### Data Protection
- [ ] Encryption at rest (AES-256-GCM)
- [ ] Encryption in transit (TLS 1.3)
- [ ] Key derivation via HKDF
- [ ] Key rotation capability
- [ ] PII redaction in logs
- [ ] Data minimization (collect only needed)
- [ ] Retention policies enforced
- [ ] GDPR/CCPA user rights implemented

### API Security
- [ ] Rate limiting (IP, user, endpoint, daily tokens)
- [ ] CORS exact origin allowlist
- [ ] Security headers (CSP, HSTS, X-Frame-Options, etc.)
- [ ] Request size limits
- [ ] Timeout enforcement
- [ ] Idempotency keys for mutations

## Observability

### Logging
- [ ] Structured JSON logging
- [ ] Correlation IDs (request_id, trace_id, span_id)
- [ ] Log levels appropriate (no debug in prod)
- [ ] PII redacted from logs
- [ ] Centralized log aggregation (ELK/Loki/Datadog)
- [ ] Log retention policy

### Metrics
- [ ] Prometheus metrics exposed
- [ ] Key metrics: latency, errors, throughput, saturation
- [ ] Business metrics: active users, cost, token usage
- [ ] Custom metrics for LLM orchestration
- [ ] Metrics retention (30d+)

### Tracing
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Trace context propagation
- [ ] Span attributes for debugging
- [ ] Sampling strategy configured

### Alerting
- [ ] Alert rules for all critical paths
- [ ] Multiple notification channels (PagerDuty, Slack, Email)
- [ ] Alert deduplication and grouping
- [ ] Runbook links in alert annotations
- [ ] Regular alert tuning (reduce noise)

### Health Checks
- [ ] Liveness probe (`/healthz`)
- [ ] Readiness probe (`/ready`)
- [ ] Startup probe (`/startup`)
- [ ] Dependency checks (DB, cache, external APIs)
- [ ] Proper HTTP status codes

## Reliability

### Resilience Patterns
- [ ] Circuit breakers for external dependencies
- [ ] Retry with exponential backoff + jitter
- [ ] Timeout budgets
- [ ] Bulkhead isolation
- [ ] Fallback models for LLM
- [ ] Graceful degradation

### Capacity Planning
- [ ] Load testing completed
- [ ] Auto-scaling configured
- [ ] Resource quotas set
- [ ] Capacity alerts (70%, 85%, 95%)

### Disaster Recovery
- [ ] Backup strategy documented
- [ ] Restore procedures tested
- [ ] RTO/RPO defined and met
- [ ] Cross-region replication for critical data
- [ ] Runbooks for common incidents
- [ ] Chaos engineering experiments

## Operational Excellence

### Deployment
- [ ] CI/CD pipeline with gates
- [ ] Automated testing (unit, integration, e2e)
- [ ] Security scanning in pipeline
- [ ] Blue-green or rolling deployments
- [ ] Rollback procedure documented and tested
- [ ] Deployment notifications

### Configuration
- [ ] Environment-specific configs
- [ ] Feature flags for gradual rollout
- [ ] Configuration validation at startup
- [ ] No hardcoded values

### Incident Management
- [ ] On-call rotation
- [ ] Escalation policies
- [ ] Status page
- [ ] Postmortem process (blameless)
- [ ] Incident communication templates

### Documentation
- [ ] Architecture diagrams
- [ ] API documentation (OpenAPI)
- [ ] Runbooks for common operations
- [ ] Disaster recovery plan
- [ ] Security incident response plan
- [ ] Data flow diagrams

## Compliance

### Data Privacy
- [ ] Data Processing Agreements with subprocessors
- [ ] Privacy policy published
- [ ] Cookie consent (if applicable)
- [ ] Data subject request process
- [ ] Data retention schedule
- [ ] Data deletion verification

### Security Standards
- [ ] SOC 2 Type II (if applicable)
- [ ] ISO 27001 controls mapped
- [ ] Penetration testing (annual)
- [ ] Vulnerability scanning (continuous)
- [ ] Security training for team

### Audit
- [ ] Audit logging for all sensitive operations
- [ ] Immutable audit logs
- [ ] Access review (quarterly)
- [ ] Compliance reporting

---

## Verification Commands

```bash
# Check container runs as non-root
docker run --rm kuro-backend whoami

# Check read-only filesystem
docker run --rm --read-only kuro-backend touch /test || echo "Read-only OK"

# Check security headers
curl -I https://api.kuro.ai/ | grep -i "x-frame\|x-content\|strict-transport"

# Check rate limiting
for i in {1..100}; do curl -s -o /dev/null -w "%{http_code}\n" https://api.kuro.ai/chat; done | sort | uniq -c

# Check health endpoints
curl -f https://api.kuro.ai/healthz
curl -f https://api.kuro.ai/ready
curl -f https://api.kuro.ai/startup

# Check metrics
curl https://api.kuro.ai/metrics | head -50

# Check TLS
openssl s_client -connect api.kuro.ai:443 -servername api.kuro.ai < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Check CORS
curl -H "Origin: https://evil.com" -H "Access-Control-Request-Method: POST" -X OPTIONS https://api.kuro.ai/chat -v

# Check authentication
curl -H "Authorization: Bearer invalid" https://api.kuro.ai/chat
```

---

## Sign-off

| Checklist Item | Verified By | Date | Notes |
|----------------|-------------|------|-------|
| Infrastructure Security | | | |
| Application Security | | | |
| Observability | | | |
| Reliability | | | |
| Operational Excellence | | | |
| Compliance | | | |

*Last updated: 2024-11-14*
*Version: 1.0*