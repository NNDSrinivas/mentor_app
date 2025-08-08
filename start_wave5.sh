#!/bin/bash
# start_wave5.sh - Start the Wave 5 approval-gated task/PR/CI system

echo "🚀 Starting Wave 5: Task/PR/CI-aware AI with Human-in-the-Loop"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your API tokens and configuration"
    echo "🔒 Remember to keep DRY_RUN=true until you're ready!"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
fi

# Install dependencies
echo "📦 Installing/updating dependencies..."
pip install -r requirements.txt

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "🔧 Configuration:"
echo "   Flask Server: ${FLASK_HOST:-0.0.0.0}:${FLASK_PORT:-8081}"
echo "   WebSocket Server: ${FLASK_HOST:-0.0.0.0}:${WS_PORT:-8001}"
echo "   Dry Run Mode: ${DRY_RUN:-true}"
echo ""

# Start the servers
echo "🌟 Starting Wave 5 servers..."
echo "   - Approvals API on port ${FLASK_PORT:-8081}"
echo "   - WebSocket notifications on port ${WS_PORT:-8001}"
echo "   - GitHub webhook endpoint: /webhook/github"
echo ""
echo "📱 Test the system:"
echo "   curl http://localhost:${FLASK_PORT:-8081}/api/health"
echo "   curl http://localhost:${FLASK_PORT:-8081}/api/approvals"
echo ""
echo "🛑 Press Ctrl+C to stop"
echo ""

# Run the server (both Flask and WebSocket)
python -m backend.server
