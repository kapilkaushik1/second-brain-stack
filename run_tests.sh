# Test runner for all test suites
pytest tests/unit/ -v --tb=short
pytest tests/integration/ -v --tb=short  
pytest tests/test_full_integration.py -v
echo "Test suite completed!"