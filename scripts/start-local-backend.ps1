# Windows PowerShell version of the backend setup script

Write-Host "🚀 Starting Kuro Backend for Local Development..." -ForegroundColor Green

# Navigate to backend directory
Set-Location backend

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Set environment variables for local development
$env:DEBUG = "True"
$env:ENVIRONMENT = "development"
$env:PORT = "8000"

# Start the backend server
Write-Host "🌟 Starting backend server on http://localhost:8000" -ForegroundColor Green
python main.py
