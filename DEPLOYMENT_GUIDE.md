# 🚀 Deployment Guide: Vercel + Render

This guide will help you deploy your Canvas Chat AI application with:
- **Frontend**: Vercel (React/Vite)
- **Backend**: Render (FastAPI/Python)

## 📋 Prerequisites

Before deploying, ensure you have:
- [ ] GitHub repository with your code
- [ ] MongoDB Atlas database (allow connections from 0.0.0.0/0)
- [ ] Pinecone account and index created
- [ ] Google Gemini API key
- [ ] Clerk account and application configured

---

## 🎯 Part 1: Backend Deployment (Render)

### 1.1 Create Render Account
1. Go to [render.com](https://render.com) and sign up
2. Connect your GitHub account

### 1.2 Deploy Backend
1. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository: `your-username/Kuro`

2. **Configure Service**
   - **Name**: `canvas-chat-backend`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3` (will use Python 3.11.9 from runtime.txt)
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn chatbot:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

3. **Environment Variables**
   Add these in the Environment section:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/chatbot?retryWrites=true&w=majority
   PINECONE_API_KEY=your-pinecone-api-key
   PINECONE_INDEX_NAME=my-chatbot-memory
   GEMINI_API_KEY=your-google-gemini-api-key
   CLERK_SECRET_KEY=sk_test_your-clerk-secret-key
   ENVIRONMENT=production
   DEBUG=false
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment
   - Note your backend URL: `https://canvas-chat-backend.onrender.com`

### 1.3 Test Backend
Visit: `https://your-backend-url.onrender.com/health`
Should return: `{"status": "healthy", "components": {...}}`

---

## 🎨 Part 2: Frontend Deployment (Vercel)

### 2.1 Create Vercel Account
1. Go to [vercel.com](https://vercel.com) and sign up
2. Connect your GitHub account

### 2.2 Deploy Frontend
1. **Import Project**
   - Click "New Project"
   - Import your GitHub repository: `your-username/Kuro`
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-detected)
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `dist` (auto-detected)
   - **Node.js Version**: 18.x (from .node-version file)

2. **Environment Variables**
   Add these in Project Settings → Environment Variables:
   ```
   VITE_CLERK_PUBLISHABLE_KEY=pk_test_your-clerk-publishable-key
   VITE_API_URL=https://your-backend-url.onrender.com
   ```

3. **Deploy**
   - Click "Deploy"
   - Wait 2-3 minutes for deployment
   - Note your frontend URL: `https://your-app.vercel.app`

### 2.3 Update Backend CORS
1. Go back to Render dashboard
2. Add environment variable:
   ```
   FRONTEND_URL=https://your-app.vercel.app
   ```
3. Redeploy backend service

---

## 🔧 Part 3: Final Configuration

### 3.1 Clerk Configuration
1. Go to your Clerk dashboard
2. **Domain Settings** → Add your Vercel URL
3. **CORS Settings** → Add both frontend and backend URLs

### 3.2 Database Verification
- **MongoDB**: Ensure Network Access allows 0.0.0.0/0
- **Pinecone**: Verify index exists with 384 dimensions
- **Test connections** from Render logs

### 3.3 Test Full Application
1. Visit your Vercel frontend URL
2. Sign up/sign in with Clerk
3. Send a test message
4. Verify chat history persists

---

## 📊 Monitoring & Maintenance

### Backend (Render)
- **Logs**: Render Dashboard → Your Service → Logs
- **Metrics**: Monitor response times and errors
- **Health Check**: `https://your-backend-url.onrender.com/health`

### Frontend (Vercel)
- **Analytics**: Vercel Dashboard → Your Project → Analytics
- **Function Logs**: Monitor for client-side errors
- **Performance**: Web Vitals tracking

---

## 🚨 Troubleshooting

### Common Issues:

1. **CORS Errors**
   - Verify `FRONTEND_URL` is set in Render
   - Check Clerk domain settings
   - Ensure URLs match exactly (no trailing slashes)

2. **Backend Errors**
   - Check Render logs for Python errors
   - Verify all environment variables are set
   - Test database connections

3. **Build Failures**
   - Verify `build.sh` has execute permissions
   - Check Python requirements compatibility
   - Monitor build logs in Render
   - **PyTorch Issues**: Ensure runtime.txt specifies Python 3.11.9
   - **Missing Dependencies**: Check requirements.txt versions
   - **Dependency Conflicts**: Use requirements-minimal.txt for emergency deployment

4. **Authentication Issues**
   - Verify Clerk publishable key matches
   - Check CORS settings in Clerk dashboard
   - Ensure JWT secrets are consistent

5. **Vercel Frontend Issues**
   - **Missing API Files**: Ensure `frontend/src/lib/api.ts` is committed to git
   - **Build Command**: Use `npm run build` (not `npm run build:prod`)
   - **Node Version**: Ensure `.node-version` file specifies Node 18.x
   - **Import Errors**: Check all import paths use correct aliases (@/)

### Debug Commands:
```bash
# Test backend health
curl https://your-backend-url.onrender.com/health

# Check API endpoints
curl https://your-backend-url.onrender.com/docs

# Alternative build command for dependency conflicts
pip install --no-cache-dir -r requirements-minimal.txt
```

---

## 🎉 Success Checklist

- [ ] Backend deployed on Render
- [ ] Frontend deployed on Vercel  
- [ ] Environment variables configured
- [ ] CORS working between frontend/backend
- [ ] Database connections established
- [ ] Clerk authentication working
- [ ] Chat functionality operational
- [ ] Session persistence working

**Your Canvas Chat AI is now live! 🚀**

**Frontend**: https://your-app.vercel.app  
**Backend**: https://your-backend-url.onrender.com  
**API Docs**: https://your-backend-url.onrender.com/docs
