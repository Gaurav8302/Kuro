# Kuro AI — Roadmap

## Vision

A production-grade, multi-model AI assistant that is fast, reliable, and context-aware — accessible to anyone via a beautiful web interface with enterprise-grade security.

## Current Phase

**v1.4.0** — Frontend Optimizations & System Stability (March 2026)

Focus: Performance optimization, lazy loading, split-screen UX fixes, simplified 4-model routing.

## Completed

### v1.0.0 — Stable Baseline (January 2025)
- Production-ready prompt system with Kuro identity
- Enterprise-grade safety system
- Intelligent memory management (MongoDB + Pinecone)
- Modern React frontend with Tailwind
- FastAPI backend with async support
- Clerk authentication integration
- Complete deployment configuration (Vercel + Render)

### v1.1.0 — Onboarding & UX (August 2025)
- First-time onboarding animation (KuroIntro)
- Session title UX (manual edit, generate button)
- Enhanced markdown & code block UX
- Mobile chat polishing

### v1.2.0 — Orchestration & Memory Compression (August 2025)
- Multi-model orchestration layer
- Model registry (YAML-driven)
- Intent classification system
- Circuit breaker + resilience patterns
- Layered memory compression (short/medium/long-term)
- Context rehydration with token budgeting
- CI workflow (GitHub Actions)

### v1.2.1 — Deployment Dependency Fix (August 2025)
- Fixed pymongo/motor version incompatibility

### v1.2.2 — Perf & Reliability Patch (August 2025)
- RAG readiness probe (Pinecone index check)
- Skill auto-reload toggle
- UTC timestamp normalization

### v1.3.0 — Skill Engine Expansion (August 2025)
- 30+ new skills with rich metadata
- Precompiled pattern matching
- Negative pattern subtraction
- Cooldown gating
- Skill debug mode

### v1.4.0 — Frontend Optimizations (March 2026)
- React lazy loading + Suspense
- Strict TypeScript (removed `any` types)
- Split-screen UX bug fixes
- Vendor chunk splitting
- Skill engine desync fixes

## In Progress

- No active development phase currently

## Planned

1. **v1.5.0** — Documentation Suite & Developer Experience
   - Structured docs (AGENTS.md, onboarding.md, architecture.md, decisions.md, memory.md, conventions.md)
   - Updated references across existing docs

2. **v2.0.0** — Speech-to-Text Integration
   - Voice input capabilities
   - Audio processing pipeline

3. **File Upload & Document Analysis**
   - PDF, image, and document processing
   - RAG over uploaded documents

## Future Ideas

- Advanced analytics dashboard
- Multi-language support (i18n)
- Plugin/extensibility system
- Enterprise team management
- Embedding-based semantic intent classification (replace regex)
- Cost & latency adaptive dynamic weight tuning
- Admin API hardening (RBAC, rate limiting)
- E2E test suite (Playwright)

## Blockers

- None currently

## Risks

- **API Provider Dependency**: Heavy reliance on Groq free tier; any API changes or rate limit tightening could impact availability
- **Cold Start**: Render free tier spin-down affects user experience for infrequent usage
- **Legacy Code**: Multiple versions of memory and routing modules create maintenance overhead
- **Test Coverage**: Frontend and E2E test suites are gaps in quality assurance
