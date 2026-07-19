@echo off
title NewsPost - Starting...

echo.
echo  ==============================
echo   NewsPost App - Starting Up
echo  ==============================
echo.

:: Start Backend (FastAPI)
echo [1/2] Starting Backend on http://localhost:8000 ...
start "NewsPost Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

:: Small delay so backend gets a head start
timeout /t 3 /nobreak >nul

:: Start Frontend (Next.js)
echo [2/2] Starting Frontend on http://localhost:3000 ...
start "NewsPost Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Open browser after a few seconds
timeout /t 5 /nobreak >nul
echo.
echo  Opening http://localhost:3000 in browser...
start "" "http://localhost:3000"

echo.
echo  Both servers are running in their own windows.
echo  Close those windows to stop the servers.
echo.
pause
