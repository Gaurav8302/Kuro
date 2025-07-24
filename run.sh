#!/bin/bash

echo "🚀 Starting Canvas Chat AI on Replit..."
echo "📦 Environment: $(if [ -n "$REPL_ID" ]; then echo "Replit Production"; else echo "Local Development"; fi)"

# Create logs directory
mkdir -p logs

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
python -m pip install --no-cache-dir -r ../requirements.txt
cd ..

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Build the frontend
echo "🏗️ Building frontend..."
npm run build:replit

echo "🔧 Configuration Summary:"
echo "  - Backend Port: ${PORT:-8000}"
echo "  - Frontend: Built and ready to serve"
echo "  - Environment: $(if [ -n "$REPL_ID" ]; then echo "Production (Replit)"; else echo "Development"; fi)"

# Start the backend server in background
echo "🚀 Starting backend server..."
cd backend
python chatbot.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 8

# Test backend health
if curl -s http://localhost:${PORT:-8000}/health > /dev/null; then
    echo "✅ Backend is healthy and running"
else
    echo "⚠️ Backend health check failed, but continuing..."
fi

# Start the frontend preview server
echo "🚀 Starting frontend preview server..."
npm run preview > logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

echo ""
echo "🎉 Canvas Chat AI is running!"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:${PORT:-8000}"
echo "📋 API Docs: http://localhost:${PORT:-8000}/docs"
echo ""

# Keep the script running and handle cleanup
cleanup() {
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup EXIT INT TERM

# Keep running
wait
