#!/bin/bash

echo "========================================"
echo "  Starting NewsPost Application"
echo "========================================"
echo ""

# Start Backend
echo "[1] Starting Backend Server..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start Frontend in the same terminal (comment out the & if you want separate terminals)
echo "[2] Starting Frontend Server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Docs:     http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop both servers..."
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
