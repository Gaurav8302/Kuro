# Kuro AI - Operational Runbooks

## Table of Contents
1. [Service Deployment](#service-deployment)
2. [Service Restart](#service-restart)
3. [Database Operations](#database-operations)
4. [Vector Store Operations](#vector-store-operations)
5. [Incident Response](#incident-response)
6. [Capacity Scaling](#capacity-scaling)
7. [Secret Rotation](#secret-rotation)
8. [Backup and Restore](#backup-and-restore)

---

## Service Deployment

### Prerequisites
- Docker and Docker Compose installed
- Access to container registry (ghcr.io)
- Environment variables configured
- Secrets available in secret manager

### Deploy to Staging
```bash
# Pull latest images
docker-compose -f docker-compose.yml pull

# Deploy with zero-downtime
docker-compose -f docker-compose.yml up -d --no-deps backend frontend

# Verify health
curl -f http://localhost:8000/healthz
curl -f http://localhost:3000/health
```

### Deploy to Production
```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml pull

# Blue-green deployment (recommended)
# 1. Deploy to green environment
# 2. Run smoke tests
# 3. Switch traffic
# 4. Decommission blue

# Or rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale backend=3 --scale frontend=2

# Verify health
curl -f https://api.kuro.ai/healthz
curl -f https://app.kuro.ai/health
```

### Rollback Procedure
```bash
# Rollback to previous version
docker-compose -f docker-compose.prod.yml down
docker tag ghcr.io/org/kuro-ai/backend:previous-sha ghcr.io/org/kuro-ai/backend:latest
docker tag ghcr.io/org/kuro-ai/frontend:previous-sha ghcr.io/org/kuro-ai/frontend:latest
docker-compose -f docker-compose.prod.yml up -d

# Verify rollback
curl -f https://api.kuro.ai/healthz
```

---

## Service Restart

### Graceful Restart (Zero Downtime)
```bash
# Backend - rolling restart
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale backend=3 backend

# Wait for new containers to be healthy
watch -n 5 'docker ps --filter "name=backend" --format "table {{.Names}}\t{{.Status}}"'

# Frontend - rolling restart
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale frontend=2 frontend
```

### Emergency Restart (With Downtime)
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Verify all services
docker-compose -f docker-compose.prod.yml ps
curl -f https://api.kuro.ai/healthz
curl -f https://app.kuro.ai/health
```

### Restart Single Service
```bash
# Restart backend only
docker-compose -f docker-compose.prod.yml restart backend

# Restart frontend only
docker-compose -f docker-compose.prod.yml restart frontend

# Restart Redis only
docker-compose -f docker-compose.prod.yml restart redis
```

---

## Database Operations

### Connect to MongoDB
```bash
# Local development
mongosh mongodb://localhost:27017/chatbot_db

# Production (via SSH tunnel)
ssh -L 27017:localhost:27017 user@prod-host
mongosh mongodb://localhost:27017/chatbot_db
```

### Common Queries

#### List all users
```javascript
db.users.find({}, {user_id: 1, name: 1, email: 1, created_at: 1})
```

#### Find user sessions
```javascript
db.sessions.find({user_id: "user_123"}).sort({created_at: -1})
```

#### Count messages per user
```javascript
db.messages.aggregate([
  {$lookup: {from: "sessions", localField: "session_id", foreignField: "session_id", as: "session"}},
  {$unwind: "$session"},
  {$group: {_id: "$session.user_id", count: {$sum: 1}}}
])
```

#### Delete user data (GDPR)
```javascript
// Get user's session IDs
var sessionIds = db.sessions.find({user_id: "user_123"}).map(s => s.session_id);

// Delete messages
db.messages.deleteMany({session_id: {$in: sessionIds}});

// Delete sessions
db.sessions.deleteMany({user_id: "user_123"});

// Delete memories
db.memories.deleteMany({user_id: "user_123"});

// Delete user profile
db.users.deleteOne({user_id: "user_123"});
```

### Backup MongoDB
```bash
# Create backup
mongodump --uri="mongodb://localhost:27017" --db=chatbot_db --out=/backups/$(date +%Y%m%d)

# Compress
tar -czf /backups/chatbot_db_$(date +%Y%m%d).tar.gz -C /backups $(date +%Y%m%d)

# Upload to S3
aws s3 cp /backups/chatbot_db_$(date +%Y%m%d).tar.gz s3://kuro-backups/mongodb/
```

### Restore MongoDB
```bash
# Download from S3
aws s3 cp s3://kuro-backups/mongodb/chatbot_db_20240115.tar.gz /tmp/

# Extract
tar -xzf /tmp/chatbot_db_20240115.tar.gz -C /tmp/

# Restore
mongorestore --uri="mongodb://localhost:27017" --db=chatbot_db --drop /tmp/20240115/chatbot_db
```

---

## Vector Store Operations

### Pinecone Index Management

#### List indexes
```bash
curl -X GET "https://api.pinecone.io/indexes" \
  -H "Api-Key: $PINECONE_API_KEY"
```

#### Create index
```bash
curl -X POST "https://api.pinecone.io/indexes" \
  -H "Api-Key: $PINECONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kuro-memories",
    "dimension": 768,
    "metric": "cosine",
    "spec": {"serverless": {"cloud": "aws", "region": "us-east-1"}}
  }'
```

#### Delete index
```bash
curl -X DELETE "https://api.pinecone.io/indexes/kuro-memories" \
  -H "Api-Key: $PINECONE_API_KEY"
```

#### Check index stats
```bash
curl -X GET "https://api.pinecone.io/indexes/kuro-memories/stats" \
  -H "Api-Key: $PINECONE_API_KEY"
```

### Delete User Vectors (GDPR)
```bash
# Using the backend API
curl -X DELETE "https://api.kuro.ai/admin/users/user_123/vectors" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV-1 | Critical outage | 15 min | API down, data loss, security breach |
| SEV-2 | Major degradation | 1 hour | High latency, partial outage, DB slow |
| SEV-3 | Minor issue | 4 hours | Non-critical feature broken, cosmetic |
| SEV-4 | Low priority | Next sprint | Enhancement, documentation |

### SEV-1 Response Procedure

1. **Acknowledge** (within 15 min)
   - Page on-call engineer
   - Create incident channel (#incident-sev1-YYYYMMDD)
   - Set incident commander

2. **Assess** (within 30 min)
   - Check health endpoints: `/healthz`, `/ready`, `/health`
   - Check logs: `docker logs backend`, `docker logs frontend`
   - Check metrics: Prometheus/Grafana dashboards
   - Check external dependencies (MongoDB, Pinecone, Groq, Clerk)

3. **Mitigate** (within 1 hour)
   - If API down: restart services, check deployments
   - If DB down: failover to replica, check connections
   - If external API down: enable fallback, circuit breaker
   - If security breach: isolate, revoke tokens, notify users

4. **Communicate**
   - Update status page
   - Notify stakeholders
   - Document timeline

5. **Resolve**
   - Implement fix
   - Verify recovery
   - Close incident
   - Schedule postmortem

### Common Incident Scenarios

#### High Error Rate
```bash
# Check error logs
docker logs backend --since 1h | grep -i error | tail -50

# Check metrics
curl http://localhost:8000/metrics | grep http_requests_total

# Common causes:
# - Database connection pool exhausted
# - LLM provider rate limiting
# - Invalid input validation
# - Memory pressure
```

#### High Latency
```bash
# Check latency metrics
curl http://localhost:8000/metrics | grep http_request_duration_seconds

# Check active requests
curl http://localhost:8000/metrics | grep llm_active_requests

# Common causes:
# - LLM provider slow
# - Database query slow
# - Memory/CPU pressure
# - Network issues
```

#### Database Connection Issues
```bash
# Check MongoDB status
mongosh --eval "db.adminCommand('ping')"

# Check connection pool
mongosh --eval "db.serverStatus().connections"

# Restart backend to reset connections
docker-compose restart backend
```

#### LLM Provider Down
```bash
# Check Groq status
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models

# Enable fallback in config
# Check active_models.py fallback_chain

# Monitor fallback usage
curl http://localhost:8000/metrics | grep llm_requests_total
```

---

## Capacity Scaling

### Horizontal Scaling (Backend)
```bash
# Scale backend replicas
docker-compose -f docker-compose.prod.yml up -d --scale backend=5

# Or with Kubernetes
kubectl scale deployment kuro-backend --replicas=5

# Verify
curl http://localhost:8000/metrics | grep llm_active_requests
```

### Vertical Scaling (Backend)
```bash
# Update docker-compose.prod.yml resources
# deploy:
#   resources:
#     limits:
#       cpus: '4'
#       memory: 4G

docker-compose -f docker-compose.prod.yml up -d --no-deps backend
```

### Database Scaling
```bash
# MongoDB - add read replicas
# Configure in MONGODB_URI: mongodb://primary,replica1,replica2/db?replicaSet=rs0

# MongoDB - sharding (for large datasets)
# sh.shardCollection("chatbot_db.messages", {"session_id": "hashed"})
```

### Vector Store Scaling
```bash
# Pinecone - increase pod size
# Update index spec in Pinecone console

# Pinecone - add replicas
# "spec": {"serverless": {"cloud": "aws", "region": "us-east-1", "replicas": 3}}
```

---

## Secret Rotation

### Rotate API Keys

#### Groq API Key
```bash
# 1. Generate new key in Groq console
# 2. Update secret in secret manager
# 3. Deploy with new key
docker-compose -f docker-compose.prod.yml up -d --no-deps backend

# 4. Verify
curl -H "Authorization: Bearer $NEW_GROQ_KEY" https://api.groq.com/openai/v1/models

# 5. Revoke old key in Groq console
```

#### Clerk Keys
```bash
# 1. Rotate in Clerk dashboard (Settings > API Keys)
# 2. Update CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY
# 3. Deploy frontend and backend
docker-compose -f docker-compose.prod.yml up -d --no-deps backend frontend

# 4. Verify authentication works
```

#### Encryption Master Key
```bash
# 1. Generate new 32-byte key
openssl rand -base64 32

# 2. Re-encrypt all data with new key (run migration script)
# 3. Update ENCRYPTION_MASTER_KEY
# 4. Deploy
docker-compose -f docker-compose.prod.yml up -d --no-deps backend

# 5. Verify encryption/decryption works
```

### Rotation Schedule
| Secret | Frequency | Automation |
|--------|-----------|------------|
| GROQ_API_KEY | 90 days | Manual |
| CLERK_SECRET_KEY | 180 days | Manual |
| MONGODB_URI | 180 days | Manual |
| PINECONE_API_KEY | 180 days | Manual |
| GEMINI_API_KEY | 90 days | Manual |
| ENCRYPTION_MASTER_KEY | 365 days | Manual + migration |
| JWT_SECRET | 90 days | Manual |
| WEBHOOK_SECRET | 90 days | Manual |

---

## Backup and Restore

### Automated Backups

#### MongoDB (Daily)
```bash
# Cron job (run at 2 AM UTC)
0 2 * * * /scripts/backup-mongodb.sh

# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
mongodump --uri="$MONGODB_URI" --db=chatbot_db --out=/backups/$DATE
tar -czf /backups/chatbot_db_$DATE.tar.gz -C /backups $DATE
aws s3 cp /backups/chatbot_db_$DATE.tar.gz s3://kuro-backups/mongodb/
rm -rf /backups/$DATE /backups/chatbot_db_$DATE.tar.gz

# Retention: keep 30 days
find /backups -name "chatbot_db_*.tar.gz" -mtime +30 -delete
aws s3 ls s3://kuro-backups/mongodb/ | awk '$1 < "'$(date -d '30 days ago' +%Y-%m-%d)'" {print $4}' | xargs -I {} aws s3 rm s3://kuro-backups/mongodb/{}
```

#### Redis (Hourly RDB)
```bash
# Redis handles RDB/AOF automatically
# Configure in redis.conf:
# save 900 1
# save 300 10
# save 60 10000
```

#### Configuration Backup
```bash
# Backup docker-compose and env files
tar -czf /backups/config_$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  docker-compose.prod.yml \
  .env.production \
  backend/Dockerfile \
  frontend/Dockerfile \
  frontend/nginx.conf

aws s3 cp /backups/config_$(date +%Y%m%d).tar.gz s3://kuro-backups/config/
```

### Disaster Recovery Plan

#### RTO/RPO Targets
| Component | RTO | RPO |
|-----------|-----|-----|
| Backend API | 15 min | 0 (stateless) |
| Frontend | 15 min | 0 (static) |
| MongoDB | 1 hour | 24 hours |
| Pinecone | 2 hours | 24 hours |
| Redis | 30 min | 1 hour |

#### Full Restore Procedure
```bash
# 1. Provision new infrastructure
# 2. Restore MongoDB from latest backup
mongorestore --uri="$MONGODB_URI" --db=chatbot_db --drop /tmp/restore/chatbot_db

# 3. Restore Pinecone (re-create index, re-ingest from MongoDB)
# Run memory re-ingestion script

# 4. Deploy application
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify all health checks
curl -f https://api.kuro.ai/health
curl -f https://app.kuro.ai/health

# 6. Run smoke tests
./scripts/smoke-tests.sh

# 7. Update DNS if needed
```

---

## Monitoring and Alerts

### Key Dashboards
- **System Health**: `/health` endpoint status
- **API Metrics**: Request rate, latency, errors
- **LLM Metrics**: Token usage, cost, provider latency
- **Database**: Connections, query latency, storage
- **Vector Store**: Index size, query latency
- **Business**: Active users, sessions, messages

### Critical Alerts
| Alert | Condition | Severity |
|-------|-----------|----------|
| API Down | `/healthz` returns 5xx | SEV-1 |
| High Error Rate | >5% 5xx errors/5min | SEV-1 |
| Database Down | MongoDB ping fails | SEV-1 |
| Vector Store Down | Pinecone ping fails | SEV-1 |
| LLM Provider Down | Groq/OpenRouter fails | SEV-1 |
| High Latency | P99 > 5s | SEV-2 |
| High Memory | >90% memory usage | SEV-2 |
| High Disk | >95% disk usage | SEV-2 |

---

## Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | PagerDuty | Primary |
| Team Lead | Slack @team-lead | Secondary |
| Engineering Manager | Slack @eng-manager | Tertiary |
| Security Team | security@kuro.ai | Security incidents |
| DBA | Slack @dba | Database issues |

---

*Last updated: 2024-11-14*
*Version: 1.0*