# Deployment Troubleshooting Guide

## Current Issues and Solutions

### 1. Import Errors (sentence_transformers)

**Problem**: 
```
ModuleNotFoundError: No module named 'sentence_transformers'
```

**Root Cause**: 
Legacy memory manager files still have heavy ML dependencies that aren't needed for production.

**Solution**:
- Use `ultra_lightweight_memory.py` instead of `memory_manager.py`
- All imports should use: `from memory.ultra_lightweight_memory import ...`
- Clear Python cache: `rm -rf backend/**/__pycache__`

**Files Fixed**:
- ✅ `backend/memory/chat_manager.py` - Using ultra-lightweight imports
- ✅ `backend/chatbot.py` - Using ultra-lightweight imports
- ✅ `backend/memory/ultra_lightweight_memory.py` - No heavy dependencies

**Files with Legacy Imports (NOT USED)**:
- ⚠️ `backend/memory/memory_manager.py` - Contains sentence_transformers
- ⚠️ `backend/memory/memory_manager_optimized.py` - Contains sentence_transformers
- ⚠️ `backend/memory/retriever.py` - Contains sentence_transformers

### 2. MongoDB Connection Issues

**Problem**:
```
ConnectionError: Database connection failed: localhost:27017
```

**Root Cause**: 
Environment variable mismatch - code looks for `MONGO_URI` but environment has `MONGODB_URI`.

**Solution**:
- Updated `backend/database/db.py` to check both `MONGODB_URI` and `MONGO_URI`
- Set environment variable in Render dashboard: `MONGODB_URI=mongodb+srv://...`

**Environment Variables Required**:
```bash
# Database
MONGODB_URI=mongodb+srv://wannabehacker0506:wH5QdVJ2tcWK5YOe@chatbot-cluster.8owjdjg.mongodb.net/?retryWrites=true&w=majority&appName=chatbot-cluster

# AI Services
GEMINI_API_KEY=AIzaSyBM5VKkTavMWfhiGGTutFfWIfvSUuhiuCg
PINECONE_API_KEY=pcsk_3pJ83v_STLzqq3RoZBxnaTGvnfuCmgmnaSoho9UiCxdzzpVNaXdkmHxNm4XFxyEnDEF16L
PINECONE_INDEX_NAME=my-chatbot-memory

# Authentication
CLERK_SECRET_KEY=sk_test_ou1X7jwlheI2glFgGC1oKttJcohi60YbJbMPwlyxyx

# CORS (Optional - defaults to frontend domains)
FRONTEND_URL=https://canvas-chat-ai-frontend.vercel.app
```

### 3. Memory Optimization for Render

**Problem**: 
```
Out of memory (used over 512Mi)
```

**Solution**:
- Using ultra-lightweight memory manager (no numpy, no scikit-learn)
- Single worker process: `gunicorn chatbot:app -w 1`
- Memory-optimized requirements.txt
- Lazy initialization of services

**Memory Usage**:
- ❌ Heavy: `memory_manager.py` (~400MB with ML libraries)
- ⚠️ Medium: `lightweight_memory.py` (~150MB with numpy)
- ✅ Ultra-light: `ultra_lightweight_memory.py` (~50MB, Google API only)

### 4. Pinecone Configuration

**Problem**:
```
Pinecone index not found
```

**Solution**:
- Environment variable: `PINECONE_INDEX_NAME=my-chatbot-memory`
- Updated all code to use correct index name
- Added error handling for index operations

### 5. Deployment Cache Issues

**Problem**: 
Deployed version using old cached imports.

**Solution**:
- Clear local `__pycache__` directories
- Force deployment refresh with git commit
- Add version comments to force file changes

## Validation Steps

Run validation script before deployment:
```bash
cd backend
python validate_deployment.py
```

## Deployment Commands

### Render Deployment
1. Connect GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy command: `gunicorn chatbot:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. Build command: `pip install -r requirements.txt`

### Manual Testing
```bash
# Test imports
python -c "from memory.ultra_lightweight_memory import ultra_lightweight_memory_manager; print('✅ Imports OK')"

# Test environment
python -c "import os; print('MONGODB_URI:', bool(os.getenv('MONGODB_URI')))"

# Test API
curl https://kuro-cemr.onrender.com/health
```

## File Structure (Production)

```
backend/
├── chatbot.py                    # ✅ Main FastAPI app
├── requirements.txt              # ✅ Memory-optimized dependencies
├── start.sh                      # ✅ Deployment script
├── validate_deployment.py        # ✅ Pre-deployment validation
├── database/
│   └── db.py                     # ✅ MongoDB connection (fixed)
├── memory/
│   ├── ultra_lightweight_memory.py  # ✅ PRODUCTION (Google API only)
│   ├── chat_manager.py              # ✅ PRODUCTION (uses ultra-lightweight)
│   ├── lightweight_memory.py        # ⚠️ BACKUP (has numpy)
│   ├── memory_manager.py            # ❌ LEGACY (heavy ML)
│   └── memory_manager_optimized.py  # ❌ LEGACY (heavy ML)
└── routes/
    └── summarize.py              # ✅ API routes
```

## Troubleshooting Commands

```bash
# Check Python imports
python -c "import sys; print(sys.path)"

# Check environment variables
env | grep -E "(MONGO|PINECONE|GEMINI|CLERK)"

# Check running processes
ps aux | grep gunicorn

# Check logs
tail -f /var/log/render.log

# Force cache clear
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

## Common Render Deployment Issues

1. **Environment Variables**: Set in Render dashboard, not in code
2. **Port Binding**: Use `0.0.0.0:$PORT` not `localhost:8000`
3. **Memory Limits**: Keep under 512MB for free tier
4. **Python Version**: Use 3.11 (matches development)
5. **Dependencies**: Keep requirements.txt minimal

## Success Indicators

✅ **Backend Health Check**: `GET /health` returns 200
✅ **Memory Usage**: Under 512MB on Render
✅ **Database Connection**: MongoDB ping successful
✅ **AI Services**: Gemini and Pinecone responding
✅ **Authentication**: Clerk validation working
✅ **CORS**: Frontend can make API calls
