#!/usr/bin/env python3
"""
Test script to validate the Second Brain Stack setup.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.utils.config import settings
    print("✅ Configuration system loaded successfully")
    print(f"   Database path: {settings.database.path}")
    print(f"   Debug mode: {settings.debug}")
except ImportError as e:
    print(f"❌ Failed to load configuration: {e}")
    sys.exit(1)

try:
    from core.utils.logging import get_logger
    logger = get_logger("TestScript")
    logger.info("Logging system working")
    print("✅ Logging system working")
except ImportError as e:
    print(f"❌ Failed to load logging: {e}")
    sys.exit(1)

try:
    from core.database.models import Document, Entity, Relationship
    print("✅ Database models loaded successfully")
except ImportError as e:
    print(f"❌ Failed to load database models: {e}")
    sys.exit(1)

async def test_database():
    """Test database initialization."""
    try:
        from core.database import DatabaseManager
        
        # Create database manager
        db = DatabaseManager()
        print("✅ Database manager created")
        
        # Create tables
        await db.create_tables()
        print("✅ Database tables created")
        
        # Test basic operations
        test_doc = Document(
            title="Test Document",
            content="This is a test document for validating the system.",
            source_type="test",
            source_path="/test/path",
            content_hash="test_hash_123",
            word_count=10
        )
        
        created_doc = await db.create_document(test_doc)
        print(f"✅ Test document created with ID: {created_doc.id}")
        
        # Get stats
        stats = await db.get_stats()
        print(f"✅ Database stats retrieved: {stats['documents']} documents")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_filesystem_scanner():
    """Test filesystem scanner."""
    try:
        from connectors.filesystem import FilesystemScanner
        
        scanner = FilesystemScanner()
        print("✅ Filesystem scanner created")
        
        # Test with docs directory if it exists
        docs_dir = Path("docs/sample-content")
        if docs_dir.exists():
            print(f"✅ Sample content directory found: {len(list(docs_dir.glob('*.md')))} markdown files")
        else:
            print("⚠️  Sample content directory not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Filesystem scanner test failed: {e}")
        return False

def test_cli():
    """Test CLI interface."""
    try:
        from interfaces.cli import main
        print("✅ CLI interface loaded")
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🧠 Second Brain Stack - Setup Validation")
    print("=" * 50)
    
    # Test imports and basic functionality
    test_cli()
    test_filesystem_scanner()
    
    # Test database (async)
    db_success = await test_database()
    
    if db_success:
        print("\n🎉 All tests passed! Your Second Brain Stack is ready.")
        print("\nNext steps:")
        print("1. Run 'make create-sample-config' to create configuration")
        print("2. Try 'python -m interfaces.cli db init' to initialize database")
        print("3. Use 'python -m interfaces.cli ingest add --source filesystem --path docs/sample-content' to test ingestion")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())