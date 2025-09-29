"""
End-to-end integration tests for the Second Brain Stack.
"""
import pytest
import httpx
import asyncio
from typing import Generator
import time


class TestE2EIntegration:
    """End-to-end integration tests."""
    
    BASE_URL = "http://localhost:8000"
    INGESTION_URL = "http://localhost:8001"
    SEARCH_URL = "http://localhost:8002"
    KNOWLEDGE_URL = "http://localhost:8003"
    CHAT_URL = "http://localhost:8004"
    
    @pytest.fixture(scope="class")
    def setup_services(self) -> Generator[None, None, None]:
        """Wait for services to be ready."""
        services = [
            ("Gateway", self.BASE_URL),
            ("Ingestion", self.INGESTION_URL),
            ("Search", self.SEARCH_URL),
            ("Knowledge", self.KNOWLEDGE_URL),
            ("Chat", self.CHAT_URL)
        ]
        
        print("\n🔧 Waiting for services to start...")
        max_retries = 30
        
        for name, url in services:
            for attempt in range(max_retries):
                try:
                    response = httpx.get(f"{url}/health", timeout=5.0)
                    if response.status_code == 200:
                        print(f"✅ {name} service ready")
                        break
                except (httpx.RequestError, httpx.TimeoutException):
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        pytest.fail(f"❌ {name} service failed to start at {url}")
        
        yield
        print("\n🧹 Test cleanup complete")
    
    @pytest.mark.asyncio
    async def test_service_health_checks(self, setup_services):
        """Test that all services are healthy."""
        services = [
            ("Gateway", self.BASE_URL),
            ("Ingestion", self.INGESTION_URL),
            ("Search", self.SEARCH_URL),
            ("Knowledge", self.KNOWLEDGE_URL),
            ("Chat", self.CHAT_URL)
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, url in services:
                response = await client.get(f"{url}/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                print(f"✅ {name} health check passed")
    
    @pytest.mark.asyncio
    async def test_document_ingestion_flow(self, setup_services):
        """Test complete document ingestion flow."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Ingest a test document
            test_doc = {
                "content": "This is a test document about artificial intelligence and machine learning.",
                "title": "Test AI Document",
                "source_type": "text",
                "source_path": "/test/document.txt"
            }
            
            print("📝 Ingesting test document...")
            response = await client.post(f"{self.INGESTION_URL}/documents", json=test_doc)
            assert response.status_code in [200, 201]
            doc_data = response.json()
            doc_id = doc_data["id"]
            print(f"✅ Document ingested with ID: {doc_id}")
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # 2. Search for the document
            print("🔍 Searching for the document...")
            search_response = await client.post(
                f"{self.SEARCH_URL}/search",
                json={"query": "artificial intelligence", "limit": 10}
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            assert len(search_data["results"]) > 0
            print(f"✅ Found {len(search_data['results'])} search results")
            
            # 3. Check knowledge extraction
            print("🧠 Checking knowledge extraction...")
            knowledge_response = await client.get(f"{self.KNOWLEDGE_URL}/entities")
            assert knowledge_response.status_code == 200
            entities_data = knowledge_response.json()
            print(f"✅ Found {len(entities_data.get('entities', []))} entities")
    
    @pytest.mark.asyncio
    async def test_chat_functionality(self, setup_services):
        """Test chat functionality."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test chat endpoint
            chat_request = {
                "message": "What can you tell me about the documents in the system?",
                "context_limit": 5
            }
            
            print("💬 Testing chat functionality...")
            response = await client.post(f"{self.CHAT_URL}/chat", json=chat_request)
            assert response.status_code == 200
            chat_data = response.json()
            assert "response" in chat_data
            assert len(chat_data["response"]) > 0
            print(f"✅ Chat responded: {chat_data['response'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_gateway_routing(self, setup_services):
        """Test that the gateway properly routes requests."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test gateway dashboard
            response = await client.get(f"{self.BASE_URL}/dashboard")
            assert response.status_code == 200
            print("✅ Gateway dashboard accessible")
            
            # Test service routing through gateway
            response = await client.get(f"{self.BASE_URL}/api/search/health")
            assert response.status_code == 200
            print("✅ Gateway routing works")


@pytest.mark.asyncio
async def test_quick_smoke_test():
    """Quick smoke test to verify basic connectivity."""
    services = [
        ("Gateway", "http://localhost:8000"),
        ("Ingestion", "http://localhost:8001"), 
        ("Search", "http://localhost:8002"),
        ("Knowledge", "http://localhost:8003"),
        ("Chat", "http://localhost:8004")
    ]
    
    print("\n🔥 Running smoke test...")
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services:
            try:
                response = await client.get(f"{url}/health")
                status = "✅ PASS" if response.status_code == 200 else f"❌ FAIL ({response.status_code})"
                print(f"{status} - {name} at {url}")
            except Exception as e:
                print(f"❌ FAIL - {name} at {url}: {str(e)}")