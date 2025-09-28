#!/bin/bash

echo "🧠 Second Brain Stack - Quick Test Suite"
echo "========================================"

# Activate virtual environment
source .venv/bin/activate

echo ""
echo "1️⃣ Testing CLI Help..."
python -m interfaces.cli --help | head -10

echo ""
echo "2️⃣ Testing Configuration..."
python -m interfaces.cli config show | head -5

echo ""
echo "3️⃣ Testing Database Initialization..."
python -m interfaces.cli db init

echo ""
echo "4️⃣ Testing Document Ingestion..."
python -m interfaces.cli ingest add --source filesystem --path docs/sample-content

echo ""
echo "5️⃣ Testing Database Statistics..."
python -m interfaces.cli db stats

echo ""
echo "6️⃣ Testing Search Functionality..."
python -m interfaces.cli search query "python" --limit 3

echo ""
echo "🎉 Quick test complete! CLI is ready for your testing."
echo ""
echo "Try these commands:"
echo "  python -m interfaces.cli search query 'machine learning'"
echo "  python -m interfaces.cli search query 'database systems'"
echo "  python -m interfaces.cli db stats"
echo ""