# Kuro Local Development Environment
# Run this script to start both frontend and backend for local development

Write-Host "Starting Kuro Local Development Environment" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Function to start backend in a new PowerShell window
function Start-Backend {
    Write-Host "Starting Backend Server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\scripts\start-local-backend.ps1"
}

# Function to start frontend in current window
function Start-Frontend {
    Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
    Set-Location frontend
    npm run dev:local
}

# Start backend in new window
Start-Backend

# Wait a moment for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend in current window
Start-Frontend
