#!/bin/bash
# Memory-optimized start script for Render free tier

# Use only 1 worker to reduce memory usage
# Disable preloading to reduce startup memory
# Use basic uvicorn worker instead of heavy gunicorn

exec gunicorn chatbot:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 1 \
  --bind 0.0.0.0:$PORT \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --timeout 60 \
  --keep-alive 30 \
  --worker-tmp-dir /dev/shm
