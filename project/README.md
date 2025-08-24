# 🤖 Kuro AI — Production-Ready Multi-Model Chatbot

![Kuro AI Banner](https://via.placeholder.com/800x200/1a1a1a/ffffff?text=Kuro+AI+-+Production+Ready+AI+Assistant)

> **A production-grade, full-stack AI chatbot** showcasing modern AI/ML integration, microservices architecture, and cloud deployment. Built with **Groq LLaMA 3 70B** for conversation, **Google Gemini embeddings** for semantic memory, and deployed on enterprise cloud infrastructure.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2+-blue.svg)](https://www.typescriptlang.org/)
[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](https://kuro-tau.vercel.app)

## 🚀 **Live Demo**
- **Frontend**: [https://kuro-tau.vercel.app](https://kuro-tau.vercel.app)
- **Backend API**: [https://kuro-ix1w.onrender.com](https://kuro-ix1w.onrender.com)

## 🏗️ **Technical Architecture**

### **Multi-Model AI Stack**
- 🧠 **Groq LLaMA 3 70B** - Primary conversation model for intelligent responses
- 🔍 **Google Gemini Embeddings** - Semantic search and memory retrieval
- 📊 **Pinecone Vector Database** - High-performance vector storage and similarity search
- 🧬 **LangChain** - AI workflow orchestration and prompt management

### **Backend Infrastructure**
- ⚡ **FastAPI** - High-performance async Python web framework
- 🗄️ **MongoDB Atlas** - Cloud-native document database for session persistence
- 🔐 **Clerk Authentication** - Enterprise-grade user management and security
- 📈 **Prometheus Metrics** - Production observability and monitoring
- 🔄 **Async/Await Patterns** - Non-blocking I/O for optimal performance

### **Frontend Technology**
- ⚛️ **React 18** - Modern component-based UI framework
- 📘 **TypeScript** - Type-safe development with enhanced developer experience
- ⚡ **Vite** - Lightning-fast development and build tooling
- 🎨 **TailwindCSS** - Utility-first styling with custom design system
- 🎬 **Framer Motion** - Smooth animations and transitions

## ✨ **Key Features**

### 🧠 **Intelligent Conversation**
- **Advanced AI Reasoning** — Powered by Groq LLaMA 3 70B for natural, context-aware responses
- **Semantic Memory** — Google Gemini embeddings for intelligent conversation history retrieval
- **Contextual Awareness** - Maintains conversation context across sessions
- **Personality Consistency** - Consistent "Kuro" AI assistant persona
- **Smart Prompt Engineering** - Production-ready system instructions with safety guardrails

### 🛡️ **Enterprise-Grade Security**
- **Content Filtering** - Multi-layered safety validation and response filtering
- **Hallucination Detection** - Prevents AI from generating false or misleading information
- **Auto-Retry Mechanism** - Automatically regenerates poor quality responses
- **Response Quality Scoring** - Ensures helpful, well-structured, and safe answers
- **CORS Protection** - Secure cross-origin resource sharing configuration

### 🧠 **Advanced Memory System**
- **Vector-Based Search** - Semantic memory retrieval using Gemini embeddings and Pinecone
- **User Profiling** - Persistent user preferences and conversation context
- **Session Management** - Maintains conversation continuity across user sessions
- **Intelligent Pruning** - Optimized memory usage for production scalability
- **Layered Compression** - Short/medium/long summaries with verbatim fact anchors
- **Context Rehydration** - Deterministic assembly under token budget constraints

### 🔐 **Authentication & Privacy**
- **Clerk Integration** - Secure user authentication with social login support
- **Privacy-First Design** - User data protection and GDPR compliance
- **Environment Security** - Secure API key management and rotation
- **Session Isolation** - Complete user data separation and security

### 🎨 **Modern User Experience**
- **Responsive Design** - Seamless experience across desktop, tablet, and mobile devices
- **Real-time Chat** - Instant message delivery with typing indicators
- **Holographic UI** - Futuristic design with smooth animations and transitions
- **Personalized Onboarding** - Animated welcome experience for new users
- **Dark/Light Theme** - Adaptive UI themes for user preference
- **Enhanced Code Rendering** - Copy single snippet or full answer, syntax highlighting
- **Session Title Control** - Manual edit and one-click AI-generated titles
- **Beautiful Interface** - Modern design with Framer Motion animations
- **Accessibility** - WCAG conscious patterns & reduced motion friendly

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   AI & Data     │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Services      │
│                 │    │                 │    │                 │
│ • React 18      │    │ • FastAPI       │    │ • Groq LLaMA 3  │
│ • TypeScript    │    │ • Python 3.11   │    │ • Gemini Embed  │
│ • Tailwind CSS  │    │ • Uvicorn       │    │ • MongoDB       │
│ • Framer Motion │    │ • Clerk Auth    │    │ • Pinecone      │
│ • Vite Build    │    │ • Observability │    │ • Vector Search │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ⚡ Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **MongoDB** database
- **API Keys** for:
  - Groq (chat generation)
  - Google Gemini (embeddings only)
  - Pinecone (vector DB)
  - Clerk (auth)
  - MongoDB (Atlas connection string)

### 1. Clone Repository

```bash
git clone https://github.com/Gaurav8302/Kuro.git
cd Kuro
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create & activate virtual environment (Windows PowerShell)
python -m venv venv
./venv/Scripts/Activate.ps1

# Or on macOS/Linux
# python3 -m venv venv
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create a .env and set the variables listed below (Backend .env)

# Start development server
uvicorn chatbot:app --reload --host 0.0.0.0 --port 8000

# Optional: use helper script (Windows)
# From repo root
# powershell -ExecutionPolicy Bypass -File .\scripts\start-local-backend.ps1
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment variables (Frontend .env)
# Set VITE_CLERK_PUBLISHABLE_KEY and VITE_API_BASE_URL (or VITE_API_URL)

# Start development server
npm run dev
```

### 4. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Core model & memory
GROQ_API_KEY=your_groq_api_key                # Chat generation (LLaMA 3 70B)
GEMINI_API_KEY=your_gemini_api_key            # Embeddings for memory

# Vector database
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
PINECONE_ENV=your_pinecone_environment

# Persistence
MONGODB_URI=your_mongodb_connection_string

# Auth
CLERK_SECRET_KEY=your_clerk_secret_key

# CORS / Frontend
FRONTEND_URL=https://your-frontend-domain.com
# Optional: allow dynamic preview domains (e.g., Vercel)
FRONTEND_URL_PATTERN=.vercel.app

# Dev toggles
DEBUG=True
ENVIRONMENT=development

# Optional: in-memory DB fallback (tests/dev only)
DISABLE_MEMORY_INIT=1
```

#### Frontend (.env.local)
```env
# API configuration
VITE_API_BASE_URL=http://localhost:8000    # or VITE_API_URL
VITE_ENVIRONMENT=development

# Authentication
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

## 📂 Project Structure

```
Kuro/
├── backend/                         # FastAPI backend
│   ├── chatbot.py                   # Main application
│   ├── database/                    # MongoDB connection & in-memory fallback
│   ├── memory/                      # Chat logic & memory
│   │   ├── chat_manager.py          # Main chat orchestration (Groq)
│   │   ├── ultra_lightweight_memory.py # Embeddings + Pinecone
│   │   └── chat_database.py         # Session/message persistence
│   ├── observability/               # Instrumentation & metrics
│   ├── admin/                       # Admin API (if enabled)
│   ├── utils/                       # Clients, prompts, helpers
│   └── requirements.txt             # Python deps
├── frontend/                        # React + Vite frontend
│   ├── src/                         # Components, pages, hooks, lib, types
│   └── vite.config.ts               # Build config
└── docs/                            # Project docs
```

## 🤖 Kuro AI System

### Personality & Identity

Kuro is designed with a consistent, helpful personality:

- **Identity**: "I am Kuro, your friendly AI assistant here to help with anything you need."
- **Tone**: Helpful, warm, and approachable
- **Communication**: Clear, concise, and kind responses
- **Expertise**: Technical knowledge with practical examples

### Safety & Observability

Multi-layered validation and visibility:

- ✅ **Content Safety** - Blocks harmful or inappropriate content
- ✅ **Accuracy** - Prevents hallucinations and false information
- ✅ **Quality** - Ensures helpful, well-structured responses
- ✅ **Privacy** - Respects user privacy and data protection
 - 📈 **Metrics** - `/metrics` endpoint exposes Prometheus metrics
 - 🔎 **Instrumentation** - Request tracing persisted to MongoDB (if Motor installed)
 - 🔁 **Health** - `/healthz`, `/live`, `/ready`, `/ping` endpoints

### Memory Management

Advanced memory system provides:

- 🧠 **Semantic Search** - Finds relevant past conversations
- 👤 **User Profiles** - Remembers preferences and context
- 💾 **Efficient Storage** - Optimized for production use
- 🔄 **Smart Pruning** - Maintains performance over time

## 🚀 Deployment

### Production Deployment

#### Backend (Render)
```bash
# Automatic deployment from GitHub
# Uses start.sh / build.sh
# Environment variables configured in Render dashboard
```

#### Frontend (Vercel)
```bash
# Automatic deployment from GitHub
# Build command: npm run build
# Environment variables configured in Vercel dashboard
```

### Docker Deployment (Alternative)

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## 🧪 Testing

### Run Tests

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test

# Selected integration tests reside in backend/ (pytest)
```

### Demo System

```bash
# Run interactive demo
python demo_kuro_system.py
```

## 📊 Performance

### Metrics
- Response time depends on model & host. Use metrics to track P95.
- Memory usage optimized via summarization and indexing.
- Cold start mitigation: `/ping` is used by the frontend to auto-warm the API.

### Monitoring
- Real-time error tracking
- Performance metrics logging
- User interaction analytics
- System health monitoring

## 🛠️ Development

### Adding Features

1. **Backend Features**: Add to `/backend/routes/`
2. **Frontend Components**: Add to `/frontend/src/components/`
3. **AI Prompts**: Modify `/backend/utils/kuro_prompt.py`
4. **Safety Rules**: Update `/backend/utils/safety.py`
5. **Routing / Orchestration**: See `/docs/ORCHESTRATION.md`
6. **Memory Architecture**: See `/docs/MEMORY_ARCHITECTURE.md`

### Code Quality

- **Linting**: ESLint (Frontend), Flake8 (Backend)
- **Formatting**: Prettier (Frontend), Black (Backend)
- **Type Checking**: TypeScript (Frontend), mypy (Backend)
- **Testing**: Jest (Frontend), pytest (Backend)

### Onboarding Intro (KuroIntro)

The animated onboarding component is displayed once per authenticated user after first successful sign-in.

Frontend integration (`Chat.tsx`):
- Checks backend: `GET /user/{user_id}/intro-shown`.
- If `false`, shows `KuroIntro`, persists with `POST /user/{user_id}/intro-shown`.
- Fallback to `localStorage` if backend unavailable.
- Auto-dismiss after ~7s or via Skip button.

Component props:
- `phrases: string[]` – cycle list (personalized first phrase supported)
- `cycleMs: number` – per phrase duration
- `fullscreen: boolean` – layout mode (only fullscreen used now)
- `onFinish?: () => void` – optional callback after a full cycle

### Key API Endpoints (selection)

Chat & Sessions:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send a message to the AI (Groq) |
| POST | `/session/create?user_id=...` | Create or reuse an empty session |
| GET | `/sessions/{user_id}` | List sessions for a user |
| GET | `/chat/{session_id}` | Get full chat history for a session |
| PUT | `/session/{session_id}` | Rename a session |
| DELETE | `/session/{session_id}` | Delete a session |

User profile & intro:

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/user/{user_id}/intro-shown` | Returns whether intro was shown | `{ user_id, intro_shown: bool }` |
| POST | `/user/{user_id}/intro-shown` | Marks intro as shown (expects `{ "shown": true }`) | `{ status, user_id, intro_shown: true }` |
| POST | `/user/{user_id}/set-name` | Persist display name | `{ status, message }` |
| GET | `/user/{user_id}/name` | Fetch display name | `{ user_id, name }` |
| GET | `/user/{user_id}/has-name` | Has display name | `{ user_id, has_name }` |

Idempotent: Multiple POSTs are safe.

### Session Title UX
- Manual edit toggles editing state; Enter saves, Escape cancels.
- Generate button disabled while generating to prevent duplicates.
- Auto-naming suppressed after user edits or generates manually.

### Markdown & Code UX
- Code blocks: copy button per block.
- Whole answer: aggregate copy button.
- Highlight.js + rehype pipeline for formatting.
- System & rate limit messages styled distinctly (`messageType`).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Groq** - High-performance LLaMA 3 70B inference
- **Google Gemini** - Embeddings (cost-effective)
- **Clerk** - Authentication infrastructure
- **MongoDB** - Reliable database solution
- **Pinecone** - Vector database for memory
- **Vercel & Render** - Deployment platforms

## 📞 Support

- 📧 **Email**: support@kuro-ai.com
- 💬 **Discord**: [Join our community](https://discord.gg/kuro-ai)
- 📖 **Documentation**: [docs.kuro-ai.com](https://docs.kuro-ai.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/Gaurav8302/Kuro/issues)

---

<div align="center">

**Made with ❤️ by the Kuro AI Team**

[Website](https://kuro-ai.com) • [Documentation](https://docs.kuro-ai.com) • [Discord](https://discord.gg/kuro-ai) • [Twitter](https://twitter.com/kuro_ai)

</div>
