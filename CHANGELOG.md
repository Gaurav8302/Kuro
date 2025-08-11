# Changelog

All notable changes to Kuro AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-08-10 - **ONBOARDING & UX ENHANCEMENTS** 🚀

## [1.2.1] - 2025-08-11 - **HOTFIX: Deployment Dependency Resolution** 🐛

### 🔧 Fixed
- Resolved Render deployment failure caused by incompatible `pymongo==4.13.2` with `motor==3.6.0` (requires `<4.10`). Downgraded to `pymongo==4.9.2` in both `backend/requirements.txt` and `backend/requirements-minimal.txt`.
- Ensured consistency across standard and minimal requirement sets to prevent future resolution divergence.

### 📝 Notes
- No code changes; pure dependency alignment. Safe patch release.
- Monitor next deployment to confirm successful environment build.

## [1.2.0] - 2025-08-11 - **ORCHESTRATION, MEMORY COMPRESSION & OPS** ⚙️🧠

### ✨ Added
- **Multi-Model Orchestration Layer**: Capability/intents aware model router with scoring (latency, quality, cost) and graceful fallback chain.
- **Model Registry**: YAML-driven registry (`backend/config/model_registry.yml`) with capabilities, default weights, and fallback configuration.
- **Intent Classification**: Lightweight rule-based classifier (keywords + overrides) powering routing decisions.
- **Circuit Breaker + Resilience**: Automatic open/half-open tracking for failing models; fallback to healthy alternatives.
- **Layered Memory Compression**: Progressive short / medium / long-term summarization with verbatim fact extraction to retain critical details.
- **Context Rehydration**: Smart assembly of prompt context (facts → summaries → recent turns) under token budget with deterministic trimming.
- **Verbatim Fact Store**: High-signal immutable facts extracted during summarization for accurate persona & knowledge grounding.
- **Token Estimator Utility**: Heuristic token counting for proactive context budgeting and overflow protection.
- **Admin & Introspection Hooks**: Foundations for secured admin endpoints (registry reload, circuit breaker stats, LLM call listing).
- **Observability Scaffolding**: Structured logging (request_id), metrics outlines, Grafana dashboard draft, Sentry hook placeholder.
- **Test Coverage Expansion**: Added tests for intent routing, fallback behavior, memory layering, and context rehydration.
- **CI Workflow**: GitHub Actions pipeline (lint + backend tests + frontend build) for PR validation.

### 🔄 Changed
- **README** expanded to document orchestration & layered memory architecture.
- **Rolling Memory Module** refactored to emit layered summaries + fact blocks while retaining original text for audit.
- **Documentation Suite**: Added `docs/ORCHESTRATION.md`, `docs/MEMORY_ARCHITECTURE.md`, and deployment optimization notes.

### 🛠️ Technical
- Deterministic prompt templates for progressive summarization ensure reproducible compression and auditability.
- Context assembly now performs deduplication & priority ordering (facts > summaries > short-term turns) with iterative token pruning.
- Registry-driven routing decouples model selection logic from application code (hot reconfig potential).

### 🧪 Quality / Reliability
- Fallback invocation verified under forced failure scenarios.
- Token budget trimming tests enforce safe degradation instead of abrupt truncation.
- Memory deduplication prevents redundant fact & summary inflation.

### ⚠️ Potential Follow-Ups
- Pluggable semantic intent classifier (embedding similarity) to augment rule set.
- Cost & latency adaptive dynamic weight tuning (feedback loop).
- Persistent metrics exporter & finalized Grafana dashboard JSON.
- Admin API hardening (API key / RBAC, rate limiting) & audit event stream.
- Advanced summarization validation (consistency / divergence detection).

---

### ✨ Added
- **First-Time Onboarding Animation**: Full-screen "KuroIntro" branded animation shown only once per authenticated user after initial sign-in.
- **Backend Persistence for Intro State**: New Mongo-backed `intro_shown` flag stored in `users` collection with REST endpoints:
	- `GET /user/{user_id}/intro-shown` → `{ intro_shown: bool }`
	- `POST /user/{user_id}/intro-shown` (body: `{ "shown": true }`) to mark as displayed (idempotent).
- **Skip / Auto-Dismiss Controls**: User can dismiss the intro early via a Skip button; auto-dismiss occurs after ~7s.
- **Personalized Welcome Phrases**: Intro cycle now greets user by first name when available.
- **Extensible Intro Component**: `KuroIntro` now accepts `phrases`, `cycleMs`, `fullscreen`, and `onFinish` callback.
- **Session Title UX Improvements**: Manual title editing, generate button, and debounce-based auto-naming suppression after manual edits.
- **Enhanced Markdown & Code Block UX**: Copy single block & full-response, syntax highlighting, safety-aware rendering.
- **Mobile Chat Polishing**: Persistent keyboard focus, tighter spacing, adaptive sidebar behavior, responsive layout refinements.
- **System & Rate Limit Messaging**: Styled system messages with type classification (rate_limit, error, warning, normal).

### 🔄 Changed
- Landing page no longer embeds the intro animation; onboarding moved to post-auth flow for cleaner marketing landing.
- Chat initialization flow now concurrently checks name setup and intro flag without blocking chat availability.

### 🛠️ Technical
- Added persistence helpers `get_intro_shown`, `set_intro_shown` in `memory/user_profile.py`.
- Added new endpoints in `chatbot.py` for intro state management.
- Frontend API layer (`src/lib/api.ts`) extended with `getIntroShown` & `setIntroShown` helpers and graceful fallback to `localStorage` if backend unavailable.
- `Chat.tsx` integrates intro overlay via `AnimatePresence` with fade transitions.

### 🧪 Quality / Reliability
- Added failsafes ensuring loading / typing indicators reset if stuck.
- Idempotent intro persistence prevents duplicate writes on refresh.

### ⚠️ Potential Follow-Ups (Not Included in 1.1.0)
- Replay intro from a user settings panel.
- Telemetry around onboarding completion.
- Progressive enhancement: reduced-motion variant for accessibility.
- Multi-tenant customization (theming / phrase injection per org).

---

## [1.0.0] - 2025-01-27 - **STABLE BASELINE RELEASE** 🎉

### **This marks the stable, production-ready baseline for Kuro AI**

### ✨ Added
- **Production-Ready Prompt System** - Advanced prompt engineering with Kuro identity
- **Enterprise-Grade Safety System** - Multi-layered content validation and hallucination detection
- **Intelligent Memory Management** - Vector-based conversation memory with MongoDB and Pinecone
- **Modern React Frontend** - Beautiful, responsive UI with TypeScript and Tailwind CSS
- **FastAPI Backend** - High-performance Python backend with async capabilities
- **Authentication System** - Secure user management with Clerk integration
- **Comprehensive Documentation** - Complete README, deployment guides, and API docs

### 🧠 **AI & Prompt Engineering**
- `utils/kuro_prompt.py` - Core prompt builder with system instructions
- `utils/safety.py` - Safety validation and response quality scoring
- Personality consistency - Maintains "Kuro" identity across conversations
- Markdown formatting support for rich responses
- Configurable personality levels (friendly, professional, casual)
- Response length controls and quality validation

### 🛡️ **Safety & Security**
- Content filtering for harmful or inappropriate responses
- Hallucination detection and prevention
- Auto-retry mechanism for poor quality responses
- CORS protection and environment variable security
- Input validation and sanitization
- Privacy-first design with secure data handling

### 🧠 **Memory System**
- Vector-based semantic search for conversation history
- User profile management and persistent preferences
- Session management with intelligent pruning
- MongoDB integration for chat history storage
- Pinecone vector database for advanced memory retrieval
- Context-aware conversation continuity

### 🎨 **Frontend Features**
- Modern React 18 with TypeScript
- Responsive design with Tailwind CSS and shadcn/ui
- Real-time chat interface with typing indicators
- Session management (create, rename, delete)
- Beautiful animations with Framer Motion
- Mobile-first responsive design
- Accessibility features and keyboard navigation

### 🚀 **Backend Architecture**
- FastAPI with async/await support
- Production-ready with Uvicorn ASGI server
- MongoDB integration for data persistence
- Pinecone vector database integration
- Google Gemini 1.5 Flash AI integration
- Comprehensive error handling and logging

### 🔧 **Development & Deployment**
- Complete environment configuration
- Docker support for containerized deployment
- Render deployment configuration for backend
- Vercel deployment configuration for frontend
- Comprehensive testing suite
- Development and production build scripts

### 📊 **Performance & Monitoring**
- Optimized for < 2s response times
- Memory usage optimized for 512MB deployments
- 99.9% uptime target architecture
- Real-time error tracking capabilities
- Performance metrics logging
- System health monitoring

### 🧪 **Testing & Quality Assurance**
- `test_kuro_system.py` - Comprehensive system tests
- `demo_kuro_system.py` - Interactive demo system
- Unit tests for core functionality
- Integration tests for API endpoints
- Safety system validation tests
- Memory system performance tests

### 📁 **Project Structure**
```
kuro/
├── backend/
│   ├── utils/           # Core AI utilities (NEW)
│   ├── memory/          # Memory management system
│   ├── routes/          # API endpoints
│   ├── database/        # Database configuration
│   └── chatbot.py       # Main application
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom hooks
│   │   └── lib/         # Utilities
│   └── package.json
└── docs/                # Documentation
```

### 🔄 **Migration & Stability**
- Full revert from previous speech-to-text implementation
- Clean codebase with no legacy technical debt
- Stable git history with clear commit messages
- Production-ready configuration
- Zero breaking changes from this baseline

### 🎯 **Production Readiness Checklist**
- ✅ AI prompt system with safety guardrails
- ✅ Memory management with vector search
- ✅ User authentication and session management
- ✅ Responsive frontend with modern UI
- ✅ Scalable backend architecture
- ✅ Comprehensive error handling
- ✅ Security features and CORS protection
- ✅ Environment configuration
- ✅ Deployment configurations
- ✅ Testing and validation suite
- ✅ Complete documentation

---

## [Previous Versions]

### [0.9.x] - Development Phase
- Basic chat functionality
- Initial AI integration
- Frontend prototype development
- Authentication system setup

### [0.8.x] - Architecture Phase
- FastAPI backend foundation
- React frontend setup
- Database integration
- Basic memory system

---

## 🚀 **What's Next?**

This stable baseline provides the foundation for future enhancements:

- **Speech-to-Text Integration** - Voice input capabilities
- **File Upload Support** - Document analysis and processing
- **Advanced Analytics** - User behavior and conversation insights
- **Multi-language Support** - International localization
- **Plugin System** - Extensible functionality
- **Enterprise Features** - Team management and collaboration

---

**Note**: This changelog will be updated with each release. The v1.0.0 baseline represents a fully functional, production-ready AI chatbot system.
