# Kuro Development Workflow Commands

## 🚀 Quick Start Development
```powershell
# Start full development environment (backend + frontend)
.\dev-start.ps1

# Or start individually:
# Backend only: .\scripts\start-local-backend.ps1
# Frontend only: cd frontend && npm run dev:local
```

## 🔄 Development Workflow

### Local Development & Testing
1. **Create Feature Branch**: `git checkout -b feature/your-feature-name`
2. **Start Dev Environment**: `.\dev-start.ps1`
3. **Test Locally**: 
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - Backend Docs: http://localhost:8000/docs

### Deploy to Testing (Vercel Preview)
```powershell
# Push feature branch (auto-deploys to Vercel preview)
git add .
git commit -m "feat: your feature description"
git push -u origin feature/your-feature-name
```
- Vercel Preview URL: `https://kuro-tau-git-feature-your-feature-name.vercel.app`
- Uses production backend: `https://kuro-cemr.onrender.com`

### Deploy to Production
```powershell
# When ready, merge to main
git checkout main
git merge feature/your-feature-name
git push origin main

# Clean up
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## 🛠️ Environment Details

### Local Development
- **Frontend**: `http://localhost:3000` → `http://localhost:8000` (local backend)
- **Backend**: Local Python server with hot reload
- **Database**: Same production MongoDB & Pinecone (shared)
- **Auth**: Same Clerk configuration

### Vercel Preview (Feature Branches)
- **Frontend**: `https://kuro-tau-git-[branch-name].vercel.app` → `https://kuro-cemr.onrender.com`
- **Backend**: Production Render backend
- **Database**: Production databases
- **Auth**: Production Clerk

### Production (Main Branch)
- **Frontend**: `https://kuro-tau.vercel.app` → `https://kuro-cemr.onrender.com`
- **Backend**: Production Render backend
- **Database**: Production databases
- **Auth**: Production Clerk

## 📝 Environment Variables

### Frontend (.env.local - Development)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
VITE_CLERK_PUBLISHABLE_KEY=pk_test_ZXhhY3QtYmVhdmVyLTU5LmNsZXJrLmFjY291bnRzLmRldiQ
```

### Frontend (.env.production - Production)
```
VITE_API_BASE_URL=https://kuro-cemr.onrender.com
VITE_ENVIRONMENT=production
VITE_CLERK_PUBLISHABLE_KEY=pk_test_ZXhhY3QtYmVhdmVyLTU5LmNsZXJrLmFjY291bnRzLmRldiQ
```

## 🐛 Troubleshooting

### CORS Issues
- Local dev: Backend runs on :8000, frontend on :3000 - already configured
- Production: Vercel frontend → Render backend - already configured

### Backend Not Starting
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend Issues
```powershell
cd frontend
npm install
npm run dev:local
```
