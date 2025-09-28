"""Test configuration and fixtures."""

import asyncio
import pytest
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

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
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """Create test settings with temporary paths."""
    test_db_path = temp_dir / "test_brain.db"
    
    settings = Settings()
    settings.database.path = str(test_db_path)
    settings.data_dir = str(temp_dir / "data")
    settings.cache_dir = str(temp_dir / "cache")
    settings.backup_dir = str(temp_dir / "backups")
    settings.debug = True
    
    return settings


@pytest.fixture
async def db_manager(test_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    """Create a test database manager."""
    db = DatabaseManager(f"sqlite+aiosqlite:///{test_settings.database.path}")
    await db.create_tables()
    
    yield db
    
    # Cleanup
    db_path = Path(test_settings.database.path)
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "title": "Machine Learning Basics",
            "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models.",
            "source_type": "test",
            "source_path": "/test/ml.txt"
        },
        {
            "title": "Python Programming", 
            "content": "Python is a high-level programming language known for its simplicity and readability.",
            "source_type": "test",
            "source_path": "/test/python.txt"
        },
        {
            "title": "Database Design",
            "content": "Database design is the process of producing a detailed data model of a database.",
            "source_type": "test", 
            "source_path": "/test/db.txt"
        }
    ]


@pytest.fixture
def sample_files(temp_dir: Path):
    """Create sample files for testing."""
    files_dir = temp_dir / "sample_files"
    files_dir.mkdir(exist_ok=True)
    
    files = {}
    
    # Create test files
    test_files = {
        "document1.txt": "This is a test document about artificial intelligence and machine learning.",
        "document2.md": "# Python Guide\n\nPython is a versatile programming language.",
        "document3.py": "# Sample Python code\ndef hello_world():\n    print('Hello, World!')",
        "ignored.pyc": "compiled python bytecode",  # Should be ignored
        "README.md": "# Project README\n\nThis is a sample project."
    }
    
    for filename, content in test_files.items():
        file_path = files_dir / filename
        file_path.write_text(content)
        files[filename] = file_path
    
    return files_dir, files