"""End-to-end tests for Second Brain Stack."""

import pytest
import requests
import time
import subprocess
import json
from pathlib import Path

# Service endpoints
GATEWAY_URL = "http://localhost:8000"
INGESTION_URL = "http://localhost:8001"
SEARCH_URL = "http://localhost:8002"
KNOWLEDGE_URL = "http://localhost:8003"
CHAT_URL = "http://localhost:8004"

class TestE2EFlow:
    """End-to-end tests for the complete Second Brain workflow."""
    
    def test_service_health_checks(self):
        """Test that all services are healthy."""
        services = {
            "gateway": GATEWAY_URL,
            "ingestion": INGESTION_URL,
            "search": SEARCH_URL,
            "knowledge": KNOWLEDGE_URL,
            "chat": CHAT_URL
        }
        
        for name, url in services.items():
            response = requests.get(f"{url}/health", timeout=10)
            assert response.status_code == 200, f"{name} service health check failed"
            assert response.json()["status"] == "healthy"
    
    def test_search_api(self):
        """Test search API functionality."""
        response = requests.post(
            f"{SEARCH_URL}/search",
            json={"query": "test query", "limit": 10},
            timeout=10
        )
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert isinstance(result["results"], list)
    
    def test_chat_api(self):
        """Test chat API functionality."""
        response = requests.post(
            f"{CHAT_URL}/message",
            json={"content": "Hello, test message"},
            timeout=10
        )
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "session_id" in result
        assert isinstance(result["response"], str)
    
    def test_knowledge_graph_api(self):
        """Test knowledge graph API."""
        response = requests.get(f"{KNOWLEDGE_URL}/entities", timeout=10)
        assert response.status_code == 200
        result = response.json()
        assert "entities" in result
        assert isinstance(result["entities"], list)
    
    def test_ingestion_api(self):
        """Test ingestion API (mock test since we don't have real files)."""
        # Test health first
        response = requests.get(f"{INGESTION_URL}/health", timeout=10)
        assert response.status_code == 200
        
        # Test stats endpoint
        response = requests.get(f"{INGESTION_URL}/stats", timeout=10)
        assert response.status_code == 200
        result = response.json()
        assert "database_stats" in result
    
    def test_gateway_routing(self):
        """Test API gateway routing."""
        # Test that gateway can route to backend services
        response = requests.get(f"{GATEWAY_URL}/health", timeout=10)
        assert response.status_code == 200
        
        # Test service discovery
        response = requests.get(f"{GATEWAY_URL}/services", timeout=10)
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, dict)

class TestCLIInterface:
    """Test the CLI interface."""
    
    def test_cli_health_check(self):
        """Test CLI health command."""
        result = subprocess.run(
            ["python", "cli.py", "health"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "HEALTHY" in result.stdout
    
    def test_cli_search(self):
        """Test CLI search command."""
        result = subprocess.run(
            ["python", "cli.py", "search", "test query"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Should return exit code 1 for no results (which is expected)
        assert result.returncode in [0, 1]
        assert "Searching for" in result.stdout
    
    def test_cli_chat(self):
        """Test CLI chat command."""
        result = subprocess.run(
            ["python", "cli.py", "chat", "hello"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "Response:" in result.stdout

class TestStackIntegration:
    """Test the full stack integration."""
    
    def test_docker_compose_services(self):
        """Test that Docker Compose services are running."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        
        # Parse JSON output
        services = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                services.append(json.loads(line))
        
        # Should have 5 services
        assert len(services) == 5
        
        # All services should be running
        running_services = [s for s in services if s.get("State") == "running"]
        assert len(running_services) == 5
    
    def test_service_communication(self):
        """Test that services can communicate with each other."""
        # Gateway should be able to reach other services
        response = requests.get(f"{GATEWAY_URL}/services", timeout=10)
        assert response.status_code == 200
        
        services_status = response.json()
        assert "ingestion" in services_status
        assert "search" in services_status
        assert "knowledge" in services_status
        assert "chat" in services_status

@pytest.fixture(scope="session", autouse=True)
def ensure_services_running():
    """Ensure services are running before tests."""
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
            if response.status_code == 200:
                break
        except requests.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                pytest.fail("Services are not running. Please start with 'make brain'")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])