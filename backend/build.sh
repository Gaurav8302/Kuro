#!/usr/bin/env bash
# Render build script for backend deployment

set -o errexit  # Exit on error

echo "🔧 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir -r requirements.txt

echo "🧪 Testing imports..."
python -c "import fastapi, uvicorn, pymongo, google.generativeai, pinecone; print('✅ Core imports successful')"

echo "✅ Build completed successfully!"
