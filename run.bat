@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  Starting NewsPost Application
echo ========================================
echo.

if not exist "backend\venv\Scripts\python.exe" (
  echo ERROR: backend\venv not found. Run setup.bat first.
  goto :end
)
if not exist "frontend\package.json" (
  echo ERROR: frontend folder missing.
  goto :end
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo ERROR: npm.cmd not found. Install Node.js and reopen the terminal.
  goto :end
)

echo [1] Starting Backend on http://127.0.0.1:8000 ...
start "NewsPost Backend" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting for backend...
ping -n 5 127.0.0.1 >nul

echo [2] Starting Frontend on http://localhost:3000 ...
start "NewsPost Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev -- -H 127.0.0.1 -p 3000"

echo Waiting for frontend (can take 10-20s first time)...
ping -n 12 127.0.0.1 >nul

echo.
echo ========================================
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo Docs:     http://127.0.0.1:8000/docs
echo ========================================
echo.
echo Keep the two black windows open while using the app.
echo If the site fails, check those windows for red errors.
echo.
start "" "http://localhost:3000"

:end
endlocal
