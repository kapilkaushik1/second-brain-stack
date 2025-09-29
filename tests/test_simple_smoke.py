"""
Simple smoke test that can be run with curl and basic tools.
"""
import subprocess
import json
import time
import sys


def test_service_health(service_name: str, url: str) -> bool:
    """Test if a service is healthy."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{url}/health"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if service_name == "Gateway":
                return data.get("gateway") == "healthy"
            else:
                return data.get("status") == "healthy"
    except Exception as e:
        print(f"❌ {service_name} failed: {e}")
    return False


def test_document_ingestion() -> bool:
    """Test basic document ingestion."""
    test_doc = {
        "content": "This is a test document about AI and machine learning.",
        "title": "Test Document",
        "source_type": "text",
        "source_path": "/test/doc.txt"
    }
    
    try:
        # Ingest document
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "http://localhost:8001/documents",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(test_doc)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return "id" in data
    except Exception as e:
        print(f"❌ Ingestion test failed: {e}")
    return False


def test_search() -> bool:
    """Test search functionality."""
    search_query = {
        "query": "artificial intelligence",
        "limit": 5
    }
    
    try:
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "http://localhost:8002/search",
            "-H", "Content-Type: application/json", 
            "-d", json.dumps(search_query)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return "results" in data
    except Exception as e:
        print(f"❌ Search test failed: {e}")
    return False


def main():
    """Run all smoke tests."""
    print("🔥 Running Second Brain Stack Smoke Tests\n")
    
    services = [
        ("Gateway", "http://localhost:8000"),
        ("Ingestion", "http://localhost:8001"),
        ("Search", "http://localhost:8002"),
        ("Knowledge", "http://localhost:8003"),
        ("Chat", "http://localhost:8004")
    ]
    
    # Test service health
    print("🏥 Testing service health...")
    health_results = []
    for name, url in services:
        is_healthy = test_service_health(name, url)
        status = "✅ PASS" if is_healthy else "❌ FAIL"
        print(f"   {status} - {name} at {url}")
        health_results.append(is_healthy)
    
    if not all(health_results):
        print("\n❌ Some services are not healthy. Fix them before continuing.")
        return False
    
    print("\n📝 Testing document ingestion...")
    ingestion_success = test_document_ingestion()
    status = "✅ PASS" if ingestion_success else "❌ FAIL"
    print(f"   {status} - Document ingestion")
    
    if ingestion_success:
        print("\n   ⏳ Waiting for document processing...")
        time.sleep(3)
        
        print("\n🔍 Testing search functionality...")
        search_success = test_search()
        status = "✅ PASS" if search_success else "❌ FAIL" 
        print(f"   {status} - Search API")
    else:
        search_success = False
    
    print("\n" + "="*50)
    if all(health_results) and ingestion_success and search_success:
        print("🎉 ALL TESTS PASSED! Stack is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the logs above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)