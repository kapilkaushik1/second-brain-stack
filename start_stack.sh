#!/bin/bash

echo "🐳 Starting Second Brain Stack - Microservices Architecture"
echo "=========================================================="
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
mkdir -p storage
mkdir -p storage/cache
mkdir -p storage/vectors
mkdir -p storage/backups

echo "📁 Created storage directories"

# Ensure database exists
if [ ! -f storage/brain.db ]; then
    echo "🗄️ Initializing database..."
    source .venv/bin/activate
    python -m interfaces.cli db init
fi

echo "🐳 Building containers..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "🎉 Second Brain Stack is running!"
echo ""
echo "📊 Service Dashboard: http://localhost:8000/dashboard"
echo ""
echo "🔗 Individual Services:"
echo "  Gateway:    http://localhost:8000"
echo "  Ingestion:  http://localhost:8001"
echo "  Search:     http://localhost:8002" 
echo "  Knowledge:  http://localhost:8003"
echo "  Chat:       http://localhost:8004"
echo ""
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "📋 Docker Status:"
docker-compose ps
echo ""
echo "📝 To view logs: docker-compose logs -f [service]"
echo "🛑 To stop: docker-compose down"