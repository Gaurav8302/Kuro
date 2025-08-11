# Deployment Guide

## Prerequisites

### Environment Variables
1. Copy `.env.example` to `.env`
2. Replace all placeholder values with your actual API keys:
   - **Clerk**: Get keys from [clerk.dev](https://clerk.dev)
   - **Google Gemini**: Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **MongoDB**: Create cluster at [MongoDB Atlas](https://cloud.mongodb.com)
   - **Pinecone**: Get API key from [Pinecone](https://pinecone.io)

### Required Services
- **MongoDB Atlas**: Vector and chat storage
- **Pinecone**: Semantic memory storage
- **Clerk**: User authentication
- **Google Gemini**: AI chat responses

## Local Development

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn chatbot:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Setup
```bash
npm install
npm run dev
```

## Production Deployment

### Environment Configuration
- Set `DEBUG=false` in production environment
- Use production-grade database connections
- Enable HTTPS
- Configure proper CORS origins for your domain

### Security Checklist
- [ ] All API keys are in environment variables (not hardcoded)
- [ ] `.env` file is not committed to version control
- [ ] DEBUG mode is disabled in production
- [ ] CORS is configured for your production domain only
- [ ] HTTPS is enabled
- [ ] Database connections use SSL
- [ ] Rate limiting is configured (if needed)

### Recommended Platforms
- **Backend**: Railway, Render, or DigitalOcean App Platform
- **Frontend**: Vercel, Netlify, or Cloudflare Pages
- **Database**: MongoDB Atlas (already cloud-hosted)
- **Vector DB**: Pinecone (already cloud-hosted)

## Health Checks

- Backend health: `GET /health`
- Root endpoint: `GET /`
- API documentation: `GET /docs` (development only)

## Monitoring

The application includes comprehensive logging. Monitor these endpoints:
- `/health` - System status and component health
- Application logs for errors and performance metrics

### Performance Tuning (Optional)
Set these if you want to optimize for cold starts / minimal I/O on constrained platforms:

```env
RAG_INDEX_CHECK_INTERVAL=300   # Cache empty index detection (seconds)
SKILL_AUTO_RELOAD_DISABLED=1   # Disable periodic skill file reload checks
```

Both have safe defaults; only override if you notice cold-start latency or file stat overhead.
