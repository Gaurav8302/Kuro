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
PORT=8000
```

## Production Setup

### Vercel Environment Variables
Set these in your Vercel dashboard:
```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_d2hvbGUtcXVhZ2dhLTQxLmNsZXJrLmFjY291bnRzLmRldiQ
VITE_API_BASE_URL=https://canvas-chat-ai.onrender.com
VITE_ENVIRONMENT=production
```

### Render Environment Variables
Set these in your Render dashboard:
```bash
MONGODB_URI=your_mongodb_connection_string
GOOGLE_API_KEY=your_google_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_pinecone_index_name
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
PORT=8000
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
