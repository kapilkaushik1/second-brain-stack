#!/bin/bash

echo "🚀 Starting Second Brain Stack - Local Development Mode"
echo "======================================================"

# Activate virtual environment
source .venv/bin/activate

# Create directories
mkdir -p storage logs

echo "📁 Storage directories ready"

# Initialize database if needed
if [ ! -f storage/brain.db ]; then
    echo "🗄️ Initializing database..."
    python -m interfaces.cli db init
fi

echo "🔧 Starting microservices..."

# Start services in background
echo "📥 Starting Ingestion Service (Port 8001)..."
python -m uvicorn services.ingestion.main:app --host 0.0.0.0 --port 8001 &
INGESTION_PID=$!

echo "🔍 Starting Search Service (Port 8002)..."  
python -m uvicorn services.search.main:app --host 0.0.0.0 --port 8002 &
SEARCH_PID=$!

echo "🕸️ Starting Knowledge Service (Port 8003)..."
python -m uvicorn services.knowledge.main:app --host 0.0.0.0 --port 8003 &
KNOWLEDGE_PID=$!

echo "💬 Starting Chat Service (Port 8004)..."
python -m uvicorn services.chat.main:app --host 0.0.0.0 --port 8004 &
CHAT_PID=$!

echo "🌐 Starting Gateway Service (Port 8000)..."
python -m uvicorn services.gateway.main:app --host 0.0.0.0 --port 8000 &
GATEWAY_PID=$!

# Save PIDs for cleanup
echo $INGESTION_PID > logs/ingestion.pid
echo $SEARCH_PID > logs/search.pid  
echo $KNOWLEDGE_PID > logs/knowledge.pid
echo $CHAT_PID > logs/chat.pid
echo $GATEWAY_PID > logs/gateway.pid

echo ""
echo "⏳ Services starting up..."
sleep 5

echo ""
echo "🎉 Second Brain Stack is running!"
echo ""
echo "📊 Gateway & Dashboard: http://localhost:8000"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "🔗 Individual Services:"
echo "  📥 Ingestion:  http://localhost:8001"
echo "  🔍 Search:     http://localhost:8002"
echo "  🕸️ Knowledge:  http://localhost:8003"  
echo "  💬 Chat:       http://localhost:8004"
echo ""
echo "📋 Test Commands:"
echo "  curl http://localhost:8000/health"
echo "  curl 'http://localhost:8002/search?q=python'"
echo "  curl http://localhost:8003/entities"
echo ""
echo "🛑 To stop all services: ./stop_services.sh"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap 'echo "Stopping services..."; kill $INGESTION_PID $SEARCH_PID $KNOWLEDGE_PID $CHAT_PID $GATEWAY_PID; exit' INT
wait