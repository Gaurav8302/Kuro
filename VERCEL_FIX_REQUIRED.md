# 🚨 CRITICAL FIX NEEDED: Vercel Environment Variable Mismatch

## The Problem
Your Vercel environment variables use a different name than what the code expects:

- **Vercel has:** `VITE_API_URL`
- **Code expects:** `VITE_API_BASE_URL`

## The Solution (Choose One)

### Option 1: Update Vercel (RECOMMENDED)
1. Go to your Vercel dashboard
2. Navigate to your project settings
3. Go to Environment Variables
4. **Rename** `VITE_API_URL` → `VITE_API_BASE_URL`
5. Keep the same value: `https://canvas-chat-ai.onrender.com`
6. Redeploy your app

### Option 2: Update Code
Update `frontend/src/lib/api.ts` to use `VITE_API_URL` instead of `VITE_API_BASE_URL`

## Current Vercel Variables (from your screenshot)
✅ `VITE_CLERK_PUBLISHABLE_KEY` - CORRECT
❌ `VITE_API_URL` - SHOULD BE `VITE_API_BASE_URL`

## Current Render Variables (from your screenshot)
✅ All variable names match code expectations perfectly:
- `CLERK_SECRET_KEY`
- `DEBUG`
- `ENVIRONMENT`
- `FRONTEND_URL`
- `GEMINI_API_KEY`
- `MONGODB_URI`
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`

## After Fix
Your frontend will properly connect to the backend at `https://canvas-chat-ai.onrender.com`
