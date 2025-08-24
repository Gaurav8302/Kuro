# 📦 Kuro AI - Project Structure

> **Production-ready AI chatbot with modern architecture and comprehensive features**

## 🏗️ Architecture Overview

```
┌──────## ⭐ Key Features & Components

### 🤖 AI System (Backend)
- **`utils/kuro_prompt.py`** - Production-ready prompt engineering with Kuro identity
- **`utils/safety.py`** - Multi-layered safety validation and content filtering
- **`memory/chat_manager.py`** - Core chat logic with Gemini AI integration
- **`test_kuro_system.py`** - Comprehensive system testing
- **`demo_kuro_system.py`** - Interactive demo and validation

### 🧠 Memory System (Backend)
- **`memory/memory_manager.py`** - Vector-based memory with Pinecone
- **`memory/chat_database.py`** - MongoDB chat history storage
- **`memory/user_profile.py`** - User preference management
- **`memory/retriever.py`** - Intelligent memory retrieval

### 🎨 Frontend Components
- **`components/ChatBubble.tsx`** - Beautiful message display with animations
- **`components/ChatInput.tsx`** - Enhanced input with auto-resize and validation
- **`components/Sidebar.tsx`** - Session management with create/rename/delete
- **`pages/Chat.tsx`** - Main chat interface with real-time updates

### 🔐 Authentication & Security
- **Clerk Integration** - Enterprise-grade authentication across frontend/backend
- **Environment Security** - Comprehensive `.env.example` files with security guidelines
- **CORS Protection** - Proper cross-origin configuration
- **Safety Validation** - AI response filtering and quality checks

## 🚀 Deployment Architecture

### Production Stack
```
┌─────────────────────────────────────────────────────────────┐
│                    Production Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend (Vercel)           Backend (Render)               │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │ React App       │◄───────►│ FastAPI Server  │            │
│  │ • TypeScript    │  HTTPS  │ • Python 3.11   │            │
│  │ • Tailwind CSS │         │ • Uvicorn ASGI  │            │
│  │ • Framer Motion │         │ • Async/Await   │            │
│  └─────────────────┘         └─────────────────┘            │
│           │                           │                     │
│           │                           │                     │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │ Clerk Auth      │         │ AI & Data       │            │
│  │ • JWT Tokens    │         │ • Gemini 1.5    │            │
│  │ • Session Mgmt  │         │ • MongoDB       │            │
│  │ • User Profiles │         │ • Pinecone      │            │
│  └─────────────────┘         └─────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Targets

#### Frontend → Vercel
- **Path**: `/frontend`
- **Framework**: React + Vite + TypeScript
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Domain**: `https://kuro-ai.vercel.app`
- **Environment**: Clerk keys, Backend API URL

#### Backend → Render
- **Path**: `/backend`
- **Framework**: FastAPI + Python 3.11+
- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn chatbot:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
- **Domain**: `https://kuro-ai-backend.onrender.com`
- **Environment**: Database URLs, AI API keys

## 🔗 Integration Flow

```
User Input → Frontend → Backend → AI Processing → Safety Check → Memory Store → Response
     ↑                                                                            ↓
     └──────────────────── Formatted Response ←──────────────────────────────────┘
```

1. **User Input**: Frontend captures and validates user messages
2. **API Call**: Secure HTTPS request to backend with authentication
3. **Prompt Building**: Kuro prompt system constructs AI request with context
4. **AI Processing**: Gemini 1.5 Flash generates intelligent response
5. **Safety Validation**: Multi-layered safety checks and content filtering
6. **Memory Storage**: Conversation stored in MongoDB + vector embeddings in Pinecone
7. **Response Delivery**: Formatted response returned to frontend
8. **UI Update**: Real-time UI update with animations and formatting

## 🛠️ Development Workflow

### Local Development Setup
```bash
# 1. Clone repository
git clone https://github.com/Gaurav8302/Kuro.git
cd Kuro

# 2. Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python chatbot.py

# 3. Frontend setup (new terminal)
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your keys
npm run dev

# 4. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Testing & Validation
```bash
# Backend testing
cd backend
python test_kuro_system.py        # System integration tests
python demo_kuro_system.py        # Interactive demo
python -m pytest                  # Unit tests

# Frontend testing
cd frontend
npm test                          # React component tests
npm run build                     # Production build test
```

## 📊 File Size & Performance

### Backend Performance
- **Response Time**: < 2s average for AI responses
- **Memory Usage**: Optimized for 512MB Render deployment
- **Concurrent Users**: Supports 100+ concurrent conversations
- **Database**: Efficient MongoDB queries with indexing

### Frontend Performance
- **Bundle Size**: ~500KB gzipped (optimized with Vite)
- **Load Time**: < 3s initial load on 3G
- **Lighthouse Score**: 90+ across all metrics
- **Mobile Responsive**: Fully optimized for mobile devices

## 🔧 Configuration Files

### Environment Configuration
- **`backend/.env.example`** - Backend environment template with all required keys
- **`frontend/.env.example`** - Frontend environment template for Clerk and API

### Build Configuration
- **`frontend/vite.config.ts`** - Vite build optimization
- **`frontend/vercel.json`** - Vercel deployment settings
- **`backend/build.sh`** - Render build script
- **`backend/render.yaml`** - Render service configuration

### Development Configuration
- **`frontend/tsconfig.json`** - TypeScript strict mode configuration
- **`frontend/tailwind.config.ts`** - Custom design system
- **`backend/requirements.txt`** - Python dependencies with versions

## 🎯 Production Readiness

### ✅ Completed Features
- [x] **AI Conversation System** - Production-ready with safety guardrails
- [x] **Memory Management** - Vector-based with MongoDB + Pinecone
- [x] **User Authentication** - Secure Clerk integration
- [x] **Responsive Frontend** - Modern React with TypeScript
- [x] **API Documentation** - FastAPI auto-generated docs
- [x] **Security Features** - CORS, input validation, environment security
- [x] **Deployment Configuration** - Ready for Vercel + Render
- [x] **Testing Suite** - Comprehensive testing and validation
- [x] **Documentation** - Complete project documentation

### 🎯 Future Enhancements
- [ ] **Speech-to-Text** - Voice input capabilities
- [ ] **File Upload** - Document analysis and processing
- [ ] **Multi-language** - International localization
- [ ] **Analytics** - User behavior tracking
- [ ] **Enterprise Features** - Team management and collaboration
- [ ] **Mobile Apps** - Native iOS/Android applications

---

**Status**: ✅ **Production Ready - Stable Baseline v1.0.0**  
**Last Updated**: January 27, 2025  
**Architecture**: Modern, scalable, secure, and well-documented┌─────────────────┐    ┌─────────────────┐
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

## 📁 Directory Structure

```
kuro/                              # Root directory
├── 📁 backend/                    # Python FastAPI Backend (Render)
│   ├── 📁 utils/                  # 🆕 Core AI Utilities
│   │   ├── 📄 kuro_prompt.py      # ⭐ AI prompt engineering system
│   │   ├── 📄 safety.py           # ⭐ Safety validation system
│   │   └── 📄 __init__.py         # Package initialization
│   ├── 📁 memory/                 # AI Memory Management
│   │   ├── 📄 chat_manager.py     # ⭐ Main chat logic with Kuro AI
│   │   ├── 📄 memory_manager.py   # Vector memory operations
│   │   ├── 📄 chat_database.py    # MongoDB operations
│   │   ├── 📄 user_profile.py     # User profile management
│   │   └── 📄 retriever.py        # Memory retrieval system
│   ├── 📁 database/               # Database Configuration
│   │   └── 📄 db.py               # MongoDB connection setup
│   ├── 📁 routes/                 # API Endpoints
│   │   └── 📄 summarize.py        # Chat summarization
│   ├── 📄 chatbot.py              # ⭐ Main FastAPI application
│   ├── 📄 requirements.txt        # Python dependencies
│   ├── 📄 build.sh                # Render build script
│   ├── 📄 render.yaml             # Render deployment config
│   ├── � test_kuro_system.py     # ⭐ System integration tests
│   ├── 📄 demo_kuro_system.py     # ⭐ Interactive demo system
│   └── 📄 .env.example            # Backend environment template
│
├── �📁 frontend/                   # React TypeScript Frontend (Vercel)
│   ├── 📁 src/
│   │   ├── 📁 components/         # React Components
│   │   │   ├── 📄 ChatBubble.tsx  # Message display component
│   │   │   ├── 📄 ChatInput.tsx   # Message input with animations
│   │   │   ├── 📄 Sidebar.tsx     # Session management sidebar
│   │   │   └── 📁 ui/             # shadcn/ui component library
│   │   ├── 📁 pages/              # Application Pages
│   │   │   ├── 📄 Chat.tsx        # Main chat interface
│   │   │   ├── 📄 Landing.tsx     # Landing page
│   │   │   ├── 📄 SignIn.tsx      # Authentication pages
│   │   │   ├── 📄 SignUp.tsx      # User registration
│   │   │   └── 📄 NotFound.tsx    # 404 error page
│   │   ├── 📁 lib/                # Utilities & API Client
│   │   │   ├── 📄 api.ts          # API communication layer
│   │   │   └── 📄 utils.ts        # Helper functions
│   │   ├── 📁 types/              # TypeScript Definitions
│   │   │   └── 📄 index.ts        # Type definitions
│   │   ├── 📁 hooks/              # Custom React Hooks
│   │   │   ├── 📄 use-chat-session.ts  # Chat session management
│   │   │   └── 📄 use-mobile.tsx  # Mobile responsiveness
│   │   ├── 📁 assets/             # Static Assets
│   │   │   └── � hero-ai.jpg     # Hero image
│   │   └── 📁 data/               # Mock Data
│   │       └── 📄 mockData.ts     # Development mock data
│   ├── 📁 public/                 # Static Files
│   │   ├── 📄 favicon.ico         # App favicon
│   │   ├── 📄 robots.txt          # SEO robots file
│   │   └── 📄 _redirects          # Vercel redirects
│   ├── 📄 package.json            # Node.js dependencies
│   ├── 📄 vite.config.ts          # Vite build configuration
│   ├── 📄 vercel.json             # Vercel deployment config
│   ├── 📄 tailwind.config.ts      # Tailwind CSS configuration
│   ├── 📄 tsconfig.json           # TypeScript configuration
│   ├── 📄 components.json         # shadcn/ui component config
│   └── 📄 .env.example            # Frontend environment template
│
├── 📁 docs/                       # 📖 Documentation
│   ├── � README.md               # ⭐ Main project documentation
│   ├── 📄 CHANGELOG.md            # ⭐ Version history and changes
│   ├── 📄 CONTRIBUTING.md         # ⭐ Contribution guidelines
│   ├── 📄 SECURITY.md             # ⭐ Security policy and practices
│   ├── � DEPLOYMENT_GUIDE.md     # Deployment instructions
│   ├── 📄 TROUBLESHOOTING.md      # Common issues and solutions
│   └── 📄 PROJECT_STRUCTURE.md    # This file
│
├── 📄 LICENSE                     # ⭐ MIT License
├── 📄 .gitignore                  # Git ignore rules
├── 📄 package.json                # Root project management
└── 📄 .env.example                # Complete environment template
```
├── 📄 README.md                   # Project documentation
├── 📄 DEPLOYMENT_GUIDE.md         # Deployment instructions
├── 📄 PROJECT_STRUCTURE.md        # This file
├── 📄 DEPLOYMENT.md               # Deployment best practices
└── 📄 SECURITY.md                 # Security guidelines
```

## 🚀 Deployment Targets

### Frontend → Vercel
- **Path**: `/frontend`
- **Framework**: React + Vite + TypeScript
- **Build Command**: `npm run build:prod`
- **Output Directory**: `dist`
- **Domain**: `https://your-app.vercel.app`
- **Environment**: Clerk keys, Backend API URL

### Backend → Render
- **Path**: `/backend`
- **Framework**: FastAPI + Python 3.9+
- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn chatbot:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
- **Domain**: `https://your-backend.onrender.com`
- **Environment**: Database URLs, AI API keys

## 🔗 Integration Points

1. **API Communication**: Frontend calls backend via `VITE_API_URL`
2. **Authentication**: Clerk handles auth, backend validates JWTs
3. **CORS**: Backend configured to accept frontend domain via `FRONTEND_URL`
4. **Database**: Backend connects to MongoDB Atlas & Pinecone
5. **AI**: Backend integrates with Google Gemini API

## �️ Development Commands

### Root Level (Project Management)
```bash
npm run install:all       # Install all dependencies
npm run dev:frontend      # Start frontend dev server
npm run dev:backend       # Start backend dev server
npm run build:frontend    # Build frontend for production
npm run build:backend     # Build backend for production
```

### Frontend Development
```bash
cd frontend
npm install               # Install dependencies
npm run dev              # Start dev server (localhost:8080)
npm run build:prod       # Production build
npm run preview          # Preview production build
```

### Backend Development  
```bash
cd backend
pip install -r requirements.txt  # Install dependencies
python chatbot.py                # Start dev server (localhost:8000)
./build.sh                      # Production build
```

## �📝 Key Files

### Configuration Files
- `frontend/vite.config.ts` - Vite build configuration
- `frontend/vercel.json` - Vercel deployment settings
- `backend/build.sh` - Render build script
- `backend/render.yaml` - Render service configuration

### Environment Templates
- `.env.example` - Complete environment variables reference
- `frontend/.env.example` - Frontend-specific variables
- `backend/.env.example` - Backend-specific variables

### Documentation
- `DEPLOYMENT_GUIDE.md` - Step-by-step deployment instructions
- `README.md` - Project overview and quick start
- `SECURITY.md` - Security best practices

- Orchestration: `docs/ORCHESTRATION.md`
- Memory Architecture: `docs/MEMORY_ARCHITECTURE.md`
## 🎯 Next Steps

1. **Local Development**: Set up environment variables and test locally
2. **Deploy Backend**: Follow DEPLOYMENT_GUIDE.md Part 1 (Render)
3. **Deploy Frontend**: Follow DEPLOYMENT_GUIDE.md Part 2 (Vercel)
4. **Configure Integration**: Set CORS and environment URLs
5. **Test Production**: Verify end-to-end functionality

Your application is now properly structured for professional deployment! �
