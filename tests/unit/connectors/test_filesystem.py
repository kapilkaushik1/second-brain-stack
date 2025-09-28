"""Unit tests for filesystem scanner."""

import pytest
from pathlib import Path
import tempfile

from connectors.filesystem import FilesystemScanner
from core.database.models import Document


@pytest.mark.asyncio
class TestFilesystemScanner:
    """Test FilesystemScanner functionality."""
    
    def test_scanner_initialization(self):
        """Test scanner initialization."""
        scanner = FilesystemScanner()
        
        # Check default supported types
        assert ".txt" in scanner.supported_types
        assert ".md" in scanner.supported_types
        assert ".py" in scanner.supported_types
        
        # Check ignore patterns
        assert "*.pyc" in scanner.ignore_patterns
        assert "__pycache__" in scanner.ignore_patterns
        assert ".git" in scanner.ignore_patterns
    
    def test_scanner_custom_types(self):
        """Test scanner with custom file types."""
        custom_types = [".txt", ".md", ".rst"]
        scanner = FilesystemScanner(supported_types=custom_types)
        
        assert scanner.supported_types == set(custom_types)
    
    async def test_scan_directory_nonexistent(self):
        """Test scanning non-existent directory."""
        scanner = FilesystemScanner()
        
        with pytest.raises(FileNotFoundError):
            await scanner.scan_directory(Path("/nonexistent/directory"))
    
    async def test_scan_directory_not_dir(self, sample_files):
        """Test scanning a file instead of directory."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        # Try to scan a file instead of directory
        file_path = files["document1.txt"]
        
        with pytest.raises(ValueError):
            await scanner.scan_directory(file_path)
    
    async def test_scan_directory_recursive(self, sample_files):
        """Test recursive directory scanning."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        # Create subdirectory with files
        subdir = files_dir / "subdir"
        subdir.mkdir()
        (subdir / "subdoc.txt").write_text("Subdirectory document")
        
        # Scan recursively
        found_files = await scanner.scan_directory(files_dir, recursive=True)
        
        # Should find files in both main dir and subdir
        found_names = [f.name for f in found_files]
        assert "document1.txt" in found_names
        assert "document2.md" in found_names
        assert "README.md" in found_names
        assert "subdoc.txt" in found_names
        
        # Should not find ignored files
        assert "ignored.pyc" not in found_names
    
    async def test_scan_directory_non_recursive(self, sample_files):
        """Test non-recursive directory scanning."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        # Create subdirectory with files
        subdir = files_dir / "subdir"
        subdir.mkdir()
        (subdir / "subdoc.txt").write_text("Subdirectory document")
        
        # Scan non-recursively
        found_files = await scanner.scan_directory(files_dir, recursive=False)
        
        # Should only find files in main directory
        found_names = [f.name for f in found_files]
        assert "document1.txt" in found_names
        assert "subdoc.txt" not in found_names  # In subdirectory
    
    def test_should_process_file(self, sample_files):
        """Test file filtering logic."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        # Should process supported file types
        assert scanner._should_process_file(files["document1.txt"])
        assert scanner._should_process_file(files["document2.md"])
        assert scanner._should_process_file(files["document3.py"])
        assert scanner._should_process_file(files["README.md"])
        
        # Should not process ignored files
        assert not scanner._should_process_file(files["ignored.pyc"])
    
    def test_parse_size_string(self):
        """Test size string parsing."""
        scanner = FilesystemScanner()
        
        assert scanner._parse_size_string("50MB") == 50 * 1024 * 1024
        assert scanner._parse_size_string("1GB") == 1024 * 1024 * 1024
        assert scanner._parse_size_string("500KB") == 500 * 1024
        assert scanner._parse_size_string("100B") == 100
        assert scanner._parse_size_string("1.5MB") == int(1.5 * 1024 * 1024)
        
        # Invalid format should return default
        assert scanner._parse_size_string("invalid") == 50 * 1024 * 1024
        assert scanner._parse_size_string("100") == 100  # Plain number
    
    async def test_process_file(self, sample_files):
        """Test processing individual files."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        # Process a text file
        document = await scanner.process_file(files["document1.txt"])
        
        assert document is not None
        assert isinstance(document, Document)
        assert document.title == "document1"  # filename without extension
        assert "artificial intelligence" in document.content
        assert document.source_type == "filesystem"
        assert document.source_path == str(files["document1.txt"].resolve())
        assert document.content_hash is not None
        assert document.word_count > 0
        assert document.doc_metadata is not None
    
    async def test_process_markdown_file(self, sample_files):
        """Test processing markdown files."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        document = await scanner.process_file(files["document2.md"])
        
        assert document is not None
        assert document.title == "document2"
        assert "Python Guide" in document.content
        assert document.source_type == "filesystem"
        assert ".md" in document.source_path
    
    async def test_process_python_file(self, sample_files):
        """Test processing Python files."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        document = await scanner.process_file(files["document3.py"])
        
        assert document is not None
        assert document.title == "document3"
        assert "def hello_world" in document.content
        assert document.source_type == "filesystem"
    
    async def test_process_empty_file(self, temp_dir):
        """Test processing empty file."""
        scanner = FilesystemScanner()
        
        # Create empty file
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")
        
        # Should return None for empty files
        document = await scanner.process_empty_file(empty_file)
        assert document is None
    
    async def test_read_file_content_encodings(self, temp_dir):
        """Test reading files with different encodings."""
        scanner = FilesystemScanner()
        
        # UTF-8 file (default)
        utf8_file = temp_dir / "utf8.txt"
        utf8_content = "Hello, 世界! 🌍"
        utf8_file.write_text(utf8_content, encoding="utf-8")
        
        content = await scanner._read_file_content(utf8_file)
        assert content == utf8_content
        
        # Latin-1 file
        latin1_file = temp_dir / "latin1.txt"
        latin1_content = "Café résumé naïve"
        latin1_file.write_text(latin1_content, encoding="latin-1")
        
        content = await scanner._read_file_content(latin1_file)
        assert "Café" in content  # Should be readable
    
    async def test_get_file_stats(self, sample_files):
        """Test getting directory statistics."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        stats = await scanner.get_file_stats(files_dir)
        
        assert stats["total_files"] > 0
        assert stats["processable_files"] > 0
        assert "by_extension" in stats
        assert "by_size_range" in stats
        
        # Check extensions
        assert ".txt" in stats["by_extension"]
        assert ".md" in stats["by_extension"]
        assert ".py" in stats["by_extension"]
        assert ".pyc" in stats["by_extension"]  # Should count all files
        
        # Processable should be less than total (due to .pyc exclusion)
        assert stats["processable_files"] <= stats["total_files"]
    
    async def test_content_hashing_consistency(self, sample_files):
        """Test that same content produces same hash."""
        files_dir, files = sample_files
        scanner = FilesystemScanner()
        
        # Process same file twice
        doc1 = await scanner.process_file(files["document1.txt"])
        doc2 = await scanner.process_file(files["document1.txt"])
        
        assert doc1.content_hash == doc2.content_hash
        
        # Different files should have different hashes
        doc3 = await scanner.process_file(files["document2.md"])
        assert doc1.content_hash != doc3.content_hash