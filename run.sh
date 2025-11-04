#!/bin/bash
# Development server startup script with automatic dependency installation

set -e  # Exit on error

echo "🚀 Starting Instagram Reels Downloader Server..."

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run: python3 -m venv .venv"
    exit 1
fi

source .venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Ensure downloads directory exists
mkdir -p downloads

# Start server
echo "✅ Starting FastAPI server..."
echo "📍 API Docs: http://localhost:8000/docs"
echo "📍 Health Check: http://localhost:8000/health"
echo ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
