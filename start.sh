#!/bin/bash
# Start the FastAPI backend server

cd "$(dirname "$0")"

echo "Starting NHL Goals Backend API..."
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "🚀 Starting server on http://localhost:8000"
echo "================================"
echo ""

# Run the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
