# Environment Configuration Guide

## Development Setup

### Frontend (.env.local)
```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_d2hvbGUtcXVhZ2dhLTQxLmNsZXJrLmFjY291bnRzLmRldiQ
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

### Backend (.env.local)
```bash
MONGODB_URI=your_mongodb_connection_string
GOOGLE_API_KEY=your_google_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_pinecone_index_name
OPENROUTER_API_KEY=your_openrouter_api_key  # Required for orchestrator layer
PORT=8000
```

## Production Setup

### Vercel Environment Variables
Set these in your Vercel dashboard (EXACT NAMES):
```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_d2hvbGUtcXVhZ2dhLTQxLmNsZXJrLmFjY291bnRzLmRldiQ
VITE_API_BASE_URL=https://kuro-cemr.onrender.com
VITE_ENVIRONMENT=production
```

**⚠️ IMPORTANT:** Your Vercel currently has `VITE_API_URL` but the code expects `VITE_API_BASE_URL`. You need to:
1. Rename `VITE_API_URL` to `VITE_API_BASE_URL` in Vercel dashboard
2. OR update the code to use `VITE_API_URL` instead

### Render Environment Variables
Set these in your Render dashboard (MATCHES YOUR CURRENT SETUP):
```bash
CLERK_SECRET_KEY=your_clerk_secret_key
MONGODB_URI=your_mongodb_connection_string
GEMINI_API_KEY=your_google_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
OPENROUTER_API_KEY=your_openrouter_api_key  # Required for orchestrator layer
DEBUG=false
ENVIRONMENT=production
FRONTEND_URL=https://your-vercel-app.vercel.app
```

## Important Notes

1. **Never commit actual .env files** - They contain sensitive information
2. **Use .env.template files** as reference for required variables
3. **Platform-specific setup**:
   - Vercel: Set environment variables in dashboard under Settings → Environment Variables
   - Render: Set environment variables in dashboard under Environment section
4. **CORS Configuration**: Backend automatically includes common origins, but you can override with ALLOWED_ORIGINS
5. **API Base URL**: Frontend automatically uses correct URL based on environment

## Local Development Commands

```bash
# Start backend
cd backend
python -m uvicorn main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend
npm run dev
```

## Production Build Commands

```bash
# Frontend production build
cd frontend
npm run build:prod

# Backend production start
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```
