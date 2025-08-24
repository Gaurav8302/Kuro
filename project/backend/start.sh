#!/bin/bash

# Ultra-lightweight start script for Render free tier
# Optimized for 512MB memory limit

echo "🚀 Starting AI Chatbot API (Ultra-Lightweight Mode)"
echo "📊 Memory optimization: Enabled"
echo "🔧 Python version: $(python --version)"

# Set memory-optimized environment variables
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export MALLOC_TRIM_THRESHOLD_=100000
export MALLOC_MMAP_THRESHOLD_=100000

# Ultra-minimal gunicorn configuration
exec gunicorn chatbot:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 180 \
    --keep-alive 30 \
    --worker-tmp-dir /dev/shm \
    --log-level info \
    --access-logfile - \
    --error-logfile -
