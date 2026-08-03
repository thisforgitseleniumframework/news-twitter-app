#!/usr/bin/env pwsh
# NewsPost Application Launcher for PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting NewsPost Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend in background
Write-Host "[1] Starting Backend Server..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "cmd" -ArgumentList '/k', "cd backend && venv\Scripts\python -m uvicorn app.main:app --reload --port 8000" -PassThru

# Wait for backend to start
Start-Sleep -Seconds 3

# Start Frontend in background
Write-Host "[2] Starting Frontend Server..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "cmd" -ArgumentList '/k', "cd frontend && npm run dev" -PassThru

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Yellow
Write-Host "Docs:     http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Both servers are starting in separate windows." -ForegroundColor White
Write-Host "Press Ctrl+C to stop..." -ForegroundColor Gray
