#!/bin/bash

echo "========================================"
echo "  NewsPost Project Setup (macOS/Linux)"
echo "========================================"

# Setup Backend
echo ""
echo "[1/4] Setting up Backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing backend dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found in backend/"
    echo "Create backend/.env with your API keys:"
    echo "  - GOOGLE_API_KEY"
    echo "  - TWITTER_API_KEY, TWITTER_API_SECRET"
    echo "  - TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET"
    echo ""
fi

cd ..

# Setup Frontend
echo ""
echo "[2/4] Setting up Frontend..."
cd frontend
echo "Installing frontend dependencies..."
npm install
cd ..

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "[3/4] To start the backend, run:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "[4/4] To start the frontend (in another terminal), run:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Docs:     http://localhost:8000/docs"
echo ""
