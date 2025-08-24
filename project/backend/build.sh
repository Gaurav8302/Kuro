#!/usr/bin/env bash
# Render build script for backend deployment

set -o errexit  # Exit on error

echo "� Python version: $(python --version)"
echo "📦 Pip version: $(pip --version)"

echo "�🔧 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install with no-deps first to avoid conflicts, then install with deps
echo "🎯 Installing core dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "🧪 Testing critical imports..."
python -c "
try:
    import fastapi, uvicorn, pymongo, pinecone
    print('✅ Core framework imports successful')
    import google.generativeai
    print('✅ Gemini API import successful')
    from dotenv import load_dotenv
    print('✅ Environment loading successful')
    print('🎉 All critical imports working!')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo "✅ Build completed successfully!"
