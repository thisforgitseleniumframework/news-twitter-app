@echo off
echo ========================================
echo  NewsPost Project Setup (Windows)
echo ========================================

REM Setup Backend
echo.
echo [1/4] Setting up Backend...
cd backend
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Installing backend dependencies...
venv\Scripts\python -m pip install -q -r requirements.txt

REM Check if .env exists
if not exist .env (
    echo.
    echo WARNING: .env file not found in backend/
    echo Create backend\.env with your API keys:
    echo   - GOOGLE_API_KEY
    echo   - TWITTER_API_KEY, TWITTER_API_SECRET
    echo   - TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
    echo.
)

cd ..

REM Setup Frontend
echo.
echo [2/4] Setting up Frontend...
cd frontend
echo Installing frontend dependencies...
call npm install
cd ..

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo [3/4] To start the backend, run:
echo   cd backend
echo   venv\Scripts\activate
echo   uvicorn app.main:app --reload
echo.
echo [4/4] To start the frontend (in another terminal), run:
echo   cd frontend
echo   npm run dev
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Docs:     http://localhost:8000/docs
echo.
pause
