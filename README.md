# 🤖 Kuro AI - Production-Ready Chatbot

![Kuro AI Banner](https://via.placeholder.com/800x200/1a1a1a/ffffff?text=Kuro+AI+-+Your+Intelligent+Assistant)

> **A modern, production-grade AI chatbot powered by Google Gemini 1.5 Flash with advanced memory management, safety guardrails, personalized onboarding, and enterprise-ready architecture.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org/)
[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](https://github.com/Gaurav8302/Kuro)

## ✨ Features

### 🧠 **Intelligent Conversation**
- **Advanced AI Reasoning** - Powered by Google Gemini 1.5 Flash
- **Contextual Memory** - Remembers conversations and user preferences
- **Personality Consistency** - Maintains "Kuro" identity across all interactions
- **Smart Prompt Engineering** - Production-ready system instructions with safety guardrails

### 🛡️ **Enterprise-Grade Safety**
- **Content Filtering** - Multi-layered safety validation system
- **Hallucination Detection** - Prevents AI from making false claims
- **Auto-Retry Mechanism** - Regenerates poor quality responses
- **Response Quality Scoring** - Ensures helpful, well-structured answers

### 🧠 **Advanced Memory System**
- **Vector-Based Search** - Semantic memory retrieval using embeddings
- **User Profiling** - Persistent user preferences and context
- **Session Management** - Maintains conversation continuity
- **Intelligent Pruning** - Optimized memory usage for production

### 🔐 **Authentication & Security**
- **Clerk Integration** - Secure user authentication and management
- **Privacy-First Design** - User data protection and GDPR compliance
- **Environment Security** - Secure API key management
- **CORS Protection** - Proper cross-origin resource sharing

### 🎨 **Modern UI/UX**
- **Personalized Onboarding** - One-time animated welcome (KuroIntro) after first sign-in
- **Responsive Design** - Works seamlessly on all devices
- **Real-time Chat** - Instant message delivery and typing indicators
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
│ • React 18      │    │ • FastAPI       │    │ • Gemini 1.5    │
│ • TypeScript    │    │ • Python 3.11   │    │ • MongoDB       │
│ • Tailwind CSS │    │ • Uvicorn       │    │ • Pinecone      │
│ • Framer Motion │    │ • Clerk Auth    │    │ • Vector Search │
│ • Vite Build    │    │ • Safety System │    │ • Memory Mgmt   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ⚡ Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **MongoDB** database
- **API Keys** for:
  - Google Gemini AI
  - Clerk Authentication
  - Pinecone Vector Database

### 1. Clone Repository

```bash
git clone https://github.com/Gaurav8302/Kuro.git
cd Kuro
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Start development server
uvicorn chatbot:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env.local
# Edit .env.local with your API keys

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
# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Authentication
CLERK_SECRET_KEY=your_clerk_secret_key

# Database
MONGO_URI=your_mongodb_connection_string

# Vector Database
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=your_pinecone_index_name
PINECONE_ENV=your_pinecone_environment

# Production
FRONTEND_URL=https://your-frontend-domain.com
```

#### Frontend (.env.local)
```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Authentication
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

## 📂 Project Structure

```
kuro/
├── backend/                    # Python FastAPI backend
│   ├── utils/                 # Core utilities
│   │   ├── kuro_prompt.py     # AI prompt engineering system
│   │   └── safety.py          # Safety validation system
│   ├── memory/                # Memory management
│   │   ├── chat_manager.py    # Main chat logic
│   │   ├── memory_manager.py  # Vector memory system
│   │   └── chat_database.py   # Database operations
│   ├── routes/                # API endpoints
│   ├── database/              # Database configuration
│   ├── requirements.txt       # Python dependencies
│   └── chatbot.py            # Main application
├── frontend/                  # React TypeScript frontend
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── lib/              # Utility functions
│   │   └── types/            # TypeScript definitions
│   ├── package.json          # Node.js dependencies
│   └── vite.config.ts        # Build configuration
└── docs/                     # Documentation
```

## 🤖 Kuro AI System

### Personality & Identity

Kuro is designed with a consistent, helpful personality:

- **Identity**: "I am Kuro, your friendly AI assistant here to help with anything you need."
- **Tone**: Helpful, warm, and approachable
- **Communication**: Clear, concise, and kind responses
- **Expertise**: Technical knowledge with practical examples

### Safety System

Multi-layered safety validation ensures:

- ✅ **Content Safety** - Blocks harmful or inappropriate content
- ✅ **Accuracy** - Prevents hallucinations and false information
- ✅ **Quality** - Ensures helpful, well-structured responses
- ✅ **Privacy** - Respects user privacy and data protection

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
# Uses build.sh for dependencies
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

# System integration test
python test_kuro_system.py
```

### Demo System

```bash
# Run interactive demo
python demo_kuro_system.py
```

## 📊 Performance

### Metrics
- **Response Time**: < 2s average
- **Memory Usage**: Optimized for 512MB deployment
- **Uptime**: 99.9% availability target
- **Safety**: 100% harmful content blocked

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

### New User Intro Persistence API

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/user/{user_id}/intro-shown` | Returns whether intro was shown | `{ user_id, intro_shown: bool }` |
| POST | `/user/{user_id}/intro-shown` | Marks intro as shown (expects `{ "shown": true }`) | `{ status, user_id, intro_shown: true }` |

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

- **Google Gemini** - Advanced AI capabilities
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
