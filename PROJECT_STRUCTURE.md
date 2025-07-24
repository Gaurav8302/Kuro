# 📦 Project Structure - Canvas Chat AI

```
canvas-chat-ai/                    # Root directory
├── 📁 frontend/                   # Vercel Deployment
│   ├── 📁 src/
│   │   ├── 📁 components/         # React components
│   │   │   ├── ChatBubble.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── 📁 ui/             # shadcn/ui components
│   │   ├── 📁 pages/              # App pages
│   │   │   ├── Chat.tsx
│   │   │   ├── Landing.tsx
│   │   │   ├── SignIn.tsx
│   │   │   └── SignUp.tsx
│   │   ├── 📁 lib/                # Utilities & API client
│   │   │   ├── api.ts
│   │   │   └── utils.ts
│   │   ├── 📁 types/              # TypeScript definitions
│   │   │   └── index.ts
│   │   ├── 📁 assets/             # Static assets
│   │   └── 📁 hooks/              # Custom React hooks
│   ├── 📁 public/                 # Static files
│   ├── 📄 package.json            # Node.js dependencies
│   ├── 📄 vite.config.ts          # Vite configuration
│   ├── 📄 vercel.json             # Vercel deployment config
│   ├── 📄 tailwind.config.ts      # Tailwind CSS config
│   ├── 📄 tsconfig.json           # TypeScript config
│   └── 📄 .env.example            # Frontend environment template
│
├── 📁 backend/                    # Render Deployment
│   ├── 📁 memory/                 # AI memory management
│   │   ├── 📄 chat_manager.py     # Chat logic with AI
│   │   ├── 📄 memory_manager.py   # Vector memory operations
│   │   ├── 📄 chat_database.py    # MongoDB operations
│   │   ├── 📄 user_profile.py     # User profile management
│   │   └── 📄 rag.py              # RAG implementation
│   ├── 📁 database/               # Database connections
│   │   └── 📄 db.py               # MongoDB setup
│   ├── 📁 routes/                 # API routes (if separated)
│   ├── 📄 chatbot.py              # Main FastAPI application
│   ├── 📄 requirements.txt        # Python dependencies
│   ├── 📄 build.sh                # Render build script
│   ├── 📄 render.yaml             # Render config (optional)
│   └── 📄 .env.example            # Backend environment template
│
├── 📄 package.json                # Root project management
├── 📄 .env.example                # Complete environment template
├── 📄 .gitignore                  # Git ignore rules
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

## 🎯 Next Steps

1. **Local Development**: Set up environment variables and test locally
2. **Deploy Backend**: Follow DEPLOYMENT_GUIDE.md Part 1 (Render)
3. **Deploy Frontend**: Follow DEPLOYMENT_GUIDE.md Part 2 (Vercel)
4. **Configure Integration**: Set CORS and environment URLs
5. **Test Production**: Verify end-to-end functionality

Your application is now properly structured for professional deployment! �
