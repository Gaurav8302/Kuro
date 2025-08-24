#!/bin/bash

# Local Development Backend Setup Script
echo "🚀 Starting Kuro Backend for Local Development..."

# Navigate to backend directory
cd backend

# Install dependencies if not already installed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set environment variables for local development
export DEBUG=True
export ENVIRONMENT=development
export PORT=8000

# Start the backend server
echo "🌟 Starting backend server on http://localhost:8000"
python main.py
