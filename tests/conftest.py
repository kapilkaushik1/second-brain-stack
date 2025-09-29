"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from core.database import DatabaseManager
from core.utils.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    settings = Settings(
        debug=True,
        environment="test",
        data_dir=str(temp_dir / "data"),
        cache_dir=str(temp_dir / "cache"),
        backup_dir=str(temp_dir / "backups"),
    )
    
    # Override database path for testing
    settings.database.path = str(temp_dir / "test.db")
    
    # Create necessary directories
    settings.create_directories()
    
    return settings


@pytest_asyncio.fixture
async def db_manager(test_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    """Create a test database manager."""
    db_manager = DatabaseManager(test_settings)
    await db_manager.create_tables()
    yield db_manager
    await db_manager.close()


@pytest_asyncio.fixture
async def db_session(db_manager: DatabaseManager):
    """Create a test database session.""" 
    # For now, just return the db_manager since we don't have separate sessions implemented yet
    yield db_manager


# Test data fixtures
@pytest.fixture
def sample_text_files(temp_dir: Path) -> list[Path]:
    """Create sample text files for testing."""
    files = []
    
    # Create some test files
    test_files = [
        ("test1.txt", "This is a test document about artificial intelligence."),
        ("test2.md", "# Machine Learning\n\nThis document covers machine learning basics."),
        ("test3.txt", "Natural language processing is fascinating."),
        ("subdir/test4.txt", "Deep learning with neural networks."),
    ]
    
    for file_path, content in test_files:
        full_path = temp_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        files.append(full_path)
    
    return files


@pytest.fixture
def sample_documents():
    """Sample document data for testing."""
    return [
        {
            "content": "Artificial intelligence is transforming technology.",
            "title": "AI Overview",
            "source_type": "text",
            "source_path": "/test/ai.txt",
            "metadata": {"author": "test_user"},
        },
        {
            "content": "Machine learning algorithms learn from data.",
            "title": "ML Basics",
            "source_type": "text", 
            "source_path": "/test/ml.txt",
            "metadata": {"category": "education"},
        },
    ]


# API client fixtures for integration tests
@pytest.fixture
def api_base_url():
    """Base URL for API tests."""
    return "http://localhost:8000"


@pytest.fixture
def ingestion_api_url():
    """Ingestion service URL."""
    return "http://localhost:8001"


@pytest.fixture
def search_api_url():
    """Search service URL."""
    return "http://localhost:8002"