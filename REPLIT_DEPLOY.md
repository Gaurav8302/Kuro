# Replit Deployment Guide

## Quick Deploy to Replit 🚀

### 1. Import to Replit
1. Go to [Replit.com](https://replit.com)
2. Click "Create Repl" → "Import from GitHub"
3. Paste your GitHub repository URL
4. Select "Python" as the language

### 2. Environment Variables Setup
Add these environment variables in Replit's "Secrets" tab (Tools → Secrets):

```
# Required - Get these from your service providers
MONGODB_URI=your_mongodb_connection_string
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
GEMINI_API_KEY=your_google_gemini_api_key
CLERK_SECRET_KEY=your_clerk_secret_key

# Replit-specific (usually auto-set)
REPL_ID=auto_set_by_replit
REPL_SLUG=your_repl_name
REPL_OWNER=your_username

# Optional
DEBUG=false
ENVIRONMENT=production
PORT=8000
```

### 3. Frontend Configuration
The frontend is automatically configured to work with Replit URLs. No changes needed!

### 4. Database Setup
Make sure your MongoDB cluster allows connections from anywhere (0.0.0.0/0) or add Replit's IP ranges.

### 5. Deploy
1. Click the "Run" button in Replit
2. Wait for dependencies to install
3. Your app will be available at: `https://your-repl-name.your-username.repl.co`

### 6. Custom Domain (Optional)
- Upgrade to Replit Pro to use custom domains
- Configure your domain to point to your Repl URL

## Architecture on Replit

```
Replit Container
├── Frontend (React + Vite) → Port 3000
├── Backend (FastAPI) → Port 8000  
├── MongoDB → External (MongoDB Atlas)
├── Pinecone → External Vector DB
└── Google Gemini → External API
```

## Performance Tips
- Use Replit's "Always On" feature for better performance
- Enable "Boost" for faster cold starts
- Monitor memory usage in the Resources tab

## Troubleshooting

### Common Issues:
1. **Port binding errors**: Replit auto-assigns ports, don't hardcode them
2. **CORS errors**: Frontend/backend URLs are automatically configured
3. **Environment variables**: Use Replit's Secrets tab, not .env files
4. **Memory limits**: Optimize dependencies in requirements.txt
5. **Cold starts**: Use "Always On" or "Boost" features

### Debug Commands:
```bash
# Check environment
env | grep -E "(REPL_|PORT|MONGODB_|PINECONE_|GEMINI_)"

# Test backend
curl http://localhost:8000/health

# Check logs
tail -f /tmp/replit.log
```

## Production Checklist ✅
- [ ] All environment variables set in Secrets
- [ ] MongoDB allows Replit connections
- [ ] Pinecone index is created and accessible
- [ ] Google Gemini API key is valid
- [ ] Clerk authentication is configured
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Backend starts without errors
- [ ] Health check endpoint responds (`/health`)
- [ ] CORS is properly configured for Replit URLs

## Monitoring
- Use Replit's built-in monitoring dashboard
- Check `/health` endpoint regularly
- Monitor error logs in the console
- Track memory usage in Resources tab

## Support
If you encounter issues:
1. Check the Replit console for error logs
2. Verify all environment variables are set
3. Test database connections
4. Check the GitHub repository for updates
