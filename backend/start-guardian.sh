#!/bin/bash

# Start equitas Guardian Backend

echo "🚀 Starting equitas Guardian Backend..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run init-uv.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your configuration"
fi

# Run database migrations (if alembic is set up)
# alembic upgrade head

# Start the server
echo "✅ Starting server on http://localhost:8000"
uvicorn guardian.main:app --reload --host 0.0.0.0 --port 8000
