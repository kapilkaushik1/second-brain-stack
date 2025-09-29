#!/usr/bin/env python3
"""
Simple CLI tool to test the Second Brain Stack.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run_curl(method: str, url: str, data: dict = None, headers: dict = None) -> dict:
    """Run curl command and return JSON response."""
    cmd = ["curl", "-s", "-X", method, url]
    
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    if data:
        cmd.extend(["-H", "Content-Type: application/json"])
        cmd.extend(["-d", json.dumps(data)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        else:
            print(f"❌ Request failed: {result.stderr}")
            return {}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}


def test_health():
    """Test all service health endpoints."""
    services = [
        ("Gateway", "http://localhost:8000"),
        ("Ingestion", "http://localhost:8001"),
        ("Search", "http://localhost:8002"),
        ("Knowledge", "http://localhost:8003"),
        ("Chat", "http://localhost:8004")
    ]
    
    print("🏥 Testing service health...\n")
    all_healthy = True
    
    for name, url in services:
        response = run_curl("GET", f"{url}/health")
        if name == "Gateway":
            is_healthy = response.get("gateway") == "healthy"
        else:
            is_healthy = response.get("status") == "healthy"
        
        status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
        print(f"{status} - {name} ({url})")
        
        if not is_healthy:
            all_healthy = False
    
    return all_healthy


def ingest_file(file_path: str):
    """Ingest a file using the ingestion service."""
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Start ingestion
    ingestion_data = {
        "source_type": "filesystem",
        "source_path": str(file_path),
        "recursive": False
    }
    
    print(f"📝 Starting ingestion of: {file_path}")
    response = run_curl("POST", "http://localhost:8001/ingest", ingestion_data)
    
    if not response:
        return False
    
    task_id = response.get("task_id")
    if not task_id:
        print("❌ No task ID received")
        return False
    
    print(f"✅ Ingestion started with task ID: {task_id}")
    
    # Monitor task status
    print("⏳ Waiting for ingestion to complete...")
    for _ in range(30):  # Wait up to 30 seconds
        status_response = run_curl("GET", f"http://localhost:8001/status/{task_id}")
        if status_response:
            status = status_response.get("status")
            processed = status_response.get("processed_files", 0)
            total = status_response.get("total_files", 0)
            
            print(f"   Status: {status}, Files: {processed}/{total}")
            
            if status == "completed":
                print("✅ Ingestion completed successfully!")
                return True
            elif status == "failed":
                errors = status_response.get("errors", [])
                print(f"❌ Ingestion failed: {errors}")
                return False
        
        time.sleep(1)
    
    print("⏰ Ingestion timed out")
    return False


def search_documents(query: str):
    """Search for documents."""
    search_data = {
        "query": query,
        "limit": 10
    }
    
    print(f"🔍 Searching for: '{query}'")
    response = run_curl("POST", "http://localhost:8002/search", search_data)
    
    if not response:
        return False
    
    results = response.get("results", [])
    print(f"✅ Found {len(results)} results:")
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        score = result.get("score", 0)
        snippet = result.get("content", "")[:100]
        print(f"   {i}. {title} (score: {score:.3f})")
        print(f"      {snippet}...")
    
    return len(results) > 0


def chat_with_brain(message: str):
    """Send a message to the chat service."""
    chat_data = {
        "content": message,
        "session_id": None,
        "context_limit": 5
    }
    
    print(f"💬 Asking: '{message}'")
    response = run_curl("POST", "http://localhost:8004/message", chat_data)
    
    if not response:
        return False
    
    reply = response.get("response", "")
    context_docs = response.get("context_documents", [])
    
    print(f"🤖 Response: {reply}")
    if context_docs:
        print(f"📚 Used {len(context_docs)} context documents")
    
    return bool(reply)


def main():
    parser = argparse.ArgumentParser(description="Second Brain CLI Testing Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health command
    subparsers.add_parser("health", help="Check service health")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a file or directory")
    ingest_parser.add_argument("path", help="Path to file or directory")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search documents")
    search_parser.add_argument("query", help="Search query")
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Chat with the brain")
    chat_parser.add_argument("message", help="Message to send")
    
    # Demo command
    subparsers.add_parser("demo", help="Run a complete demo")
    
    args = parser.parse_args()
    
    if args.command == "health":
        success = test_health()
        sys.exit(0 if success else 1)
    
    elif args.command == "ingest":
        success = ingest_file(args.path)
        sys.exit(0 if success else 1)
    
    elif args.command == "search":
        success = search_documents(args.query)
        sys.exit(0 if success else 1)
    
    elif args.command == "chat":
        success = chat_with_brain(args.message)
        sys.exit(0 if success else 1)
    
    elif args.command == "demo":
        print("🧠 Running Second Brain Stack Demo\n")
        
        # 1. Check health
        if not test_health():
            print("\n❌ Services not healthy. Fix them first.")
            sys.exit(1)
        
        print("\n" + "="*50)
        
        # 2. Create test file
        test_file = Path("/tmp/test_brain_doc.txt")
        test_content = """
        Artificial Intelligence and Machine Learning
        
        Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves algorithms and statistical models that allow systems to automatically learn and make decisions or predictions based on data.
        
        Key concepts include:
        - Neural networks and deep learning
        - Natural language processing
        - Computer vision
        - Reinforcement learning
        """
        
        test_file.write_text(test_content.strip())
        print(f"📄 Created test document: {test_file}")
        
        # 3. Ingest the file
        if not ingest_file(str(test_file)):
            print("\n❌ Ingestion failed")
            sys.exit(1)
        
        print("\n" + "="*50)
        
        # 4. Search for content
        if not search_documents("machine learning"):
            print("\n❌ Search failed")
            sys.exit(1)
        
        print("\n" + "="*50)
        
        # 5. Chat about the content
        if not chat_with_brain("What do you know about machine learning?"):
            print("\n❌ Chat failed")
            sys.exit(1)
        
        # Cleanup
        test_file.unlink()
        print(f"\n🧹 Cleaned up test file")
        
        print("\n🎉 Demo completed successfully! The Second Brain Stack is working.")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()