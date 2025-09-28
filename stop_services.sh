#!/bin/bash

echo "🛑 Stopping Second Brain Stack services..."

# Kill services by PID if files exist
if [ -f logs/ingestion.pid ]; then
    kill $(cat logs/ingestion.pid) 2>/dev/null
    rm logs/ingestion.pid
    echo "📥 Ingestion service stopped"
fi

if [ -f logs/search.pid ]; then
    kill $(cat logs/search.pid) 2>/dev/null
    rm logs/search.pid
    echo "🔍 Search service stopped"
fi

if [ -f logs/knowledge.pid ]; then
    kill $(cat logs/knowledge.pid) 2>/dev/null
    rm logs/knowledge.pid
    echo "🕸️ Knowledge service stopped"
fi

if [ -f logs/chat.pid ]; then
    kill $(cat logs/chat.pid) 2>/dev/null
    rm logs/chat.pid
    echo "💬 Chat service stopped"
fi

if [ -f logs/gateway.pid ]; then
    kill $(cat logs/gateway.pid) 2>/dev/null
    rm logs/gateway.pid
    echo "🌐 Gateway service stopped"
fi

# Also kill any remaining uvicorn processes for this project
pkill -f "uvicorn.*8001"
pkill -f "uvicorn.*8002"  
pkill -f "uvicorn.*8003"
pkill -f "uvicorn.*8004"
pkill -f "uvicorn.*8000"

echo "✅ All services stopped"