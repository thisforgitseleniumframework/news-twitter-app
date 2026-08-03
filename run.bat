@echo off
echo ========================================
echo  Starting NewsPost Application
echo ========================================
echo.

REM Start Backend in one window (using venv python directly)
echo [1] Starting Backend Server...
start cmd /k "cd backend && venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"

REM Wait a moment, then start Frontend
timeout /t 3 /nobreak

echo [2] Starting Frontend Server...
start cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Docs:     http://localhost:8000/docs
echo ========================================
echo.
echo Both servers are starting in separate windows.
echo Press any key to close this window...
pause
