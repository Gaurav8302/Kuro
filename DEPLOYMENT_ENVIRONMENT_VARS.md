# 🚀 DEPLOYMENT ENVIRONMENT VARIABLES

## ✅ ALL TESTS PASSED! Your AI setup is working correctly.

> ⚠️ **SECURITY NOTE:** Replace all placeholder values below with your actual API keys from `backend/.env`. Never commit real API keys to version control.

### **RENDER (Backend) Environment Variables**

Add these environment variables to your Render service (replace with your actual values from backend/.env):

```bash
# AI Configuration
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: OpenRouter (enables Anthropic/OpenAI via OpenRouter)
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# Optional overrides (JSON mapping of canonical IDs to OpenRouter slugs)
# OPENROUTER_MODEL_MAP={"claude-3.5-sonnet":"anthropic/claude-3.5-sonnet-20241022"}
# Optional headers recommended by OpenRouter
# OPENROUTER_REFERER=https://your-frontend-domain.vercel.app
# OPENROUTER_SITE_NAME=Kuro AI

# Authentication
CLERK_SECRET_KEY=your_clerk_secret_key_here

# Database Configuration
MONGODB_URI=your_mongodb_connection_string_here

# Vector Database
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX=my-chatbot-memory
PINECONE_ENV=us-east-1

# Frontend URL(s) and patterns (for Vercel preview domains)
FRONTEND_URL=https://your-frontend-domain.vercel.app
# Optionally allow all Vercel preview URLs:
FRONTEND_URL_PATTERN=.vercel.app

// Production Settings
ENVIRONMENT=production
DEBUG=False
# Render sets PORT automatically

# Optional Performance Tuning
# Cache RAG index readiness probe results (seconds)
RAG_INDEX_CHECK_INTERVAL=300
# Disable skill auto-reload file stat loop (set to 1 in production if not hot-editing skills)
SKILL_AUTO_RELOAD_DISABLED=1
```

### **VERCEL (Frontend) Environment Variables**

Add these environment variables to your Vercel project (replace with your actual values from backend/.env):

```bash
# Authentication
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key_here

# Backend API (Render backend URL)
VITE_API_URL=https://your-backend-service.onrender.com
```

## 🔧 **Migration Summary**

### ✅ **What's Working:**
- **Chat Responses:** Groq LLaMA 3 70B (Premium quality)
- **Embeddings:** Google Gemini (Free tier) 
- **Memory System:** Pinecone + Gemini embeddings
- **Authentication:** Clerk
- **Database:** MongoDB
- **Session Cleanup:** Groq-powered summaries

### 💰 **Cost Structure:**
- **Groq:** Pay-per-use for chat responses (very reasonable)
- **Gemini:** FREE for embeddings (stays within free tier)
- **Total:** Only paying for Groq chat usage

### 🚨 **Important Notes:**

1. **NO OpenAI API Key Needed** - We kept Gemini for free embeddings
2. **Hybrid Approach** - Best of both worlds (quality + cost efficiency)  
3. **Fully Compatible** - All existing features preserved
4. **Production Ready** - All tests passed

### 📋 **Deployment Checklist:**

#### Render (Backend):
- [ ] Update environment variables with values above
- [ ] Ensure `requirements.txt` includes `requests>=2.32.3`
- [ ] Deploy and test health endpoint

#### Vercel (Frontend):  
- [ ] Update environment variables with values above
- [ ] Test frontend-backend connection
- [ ] Verify chat functionality

### 🧪 **Testing Commands:**

After deployment, test with:

```bash
# Test backend health
curl -sSf "https://your-backend-service.onrender.com/healthz"

# Check metrics (if exposed)
curl -sSf "https://your-backend-service.onrender.com/metrics"
```

### 🎯 **Key Changes Made:**

1. **Chat Manager** - Now uses Groq LLaMA 3 70B for responses
2. **Memory System** - Still uses free Gemini embeddings  
3. **Session Cleanup** - Now uses Groq for summarization
4. **Environment** - Added GROQ_API_KEY, kept GEMINI_API_KEY
5. **Dependencies** - Added `requests` for Groq API calls

---

**🎉 Your chatbot is now powered by Groq LLaMA 3 70B with cost-optimized embeddings!**
