"""Filesystem connector for document ingestion."""

import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional, Set

from core.database import Document
from core.utils import get_logger


class FilesystemScanner:
    """Scanner for filesystem-based document ingestion."""
    
    def __init__(self, supported_types: Optional[List[str]] = None, ignore_patterns: Optional[List[str]] = None):
        self.logger = get_logger(__name__)
        
        self.supported_types = set(supported_types) if supported_types else {
            '.txt', '.md', '.pdf', '.docx', '.py', '.js', '.cpp', '.h', '.ts'
        }
        
        self.ignore_patterns = set(ignore_patterns) if ignore_patterns else {
            '.git', '__pycache__', 'node_modules', '.env', '*.pyc'
        }
        
        self.logger.info(
            "FilesystemScanner initialized",
            supported_types=list(self.supported_types),
            ignore_patterns=list(self.ignore_patterns)
        )
    
    async def scan_directory(self, directory_path: Path, recursive: bool = True) -> List[Path]:
        """Scan directory for supported files."""
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not directory_path.is_dir():
            # If it's a single file, check if we should process it
            if self._should_process_file(directory_path):
                return [directory_path]
            else:
                raise ValueError(f"Single file not supported: {directory_path}")
        
        files = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in directory_path.glob(pattern):
            if self._should_process_file(file_path):
                files.append(file_path)
        
        self.logger.info(f"Found {len(files)} files to process")
        return files
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        # Skip if not a file
        if not file_path.is_file():
            return False
        
        # Skip if extension not supported
        if file_path.suffix.lower() not in self.supported_types:
            return False
        
        # Skip if matches ignore patterns
        for pattern in self.ignore_patterns:
            if pattern in str(file_path):
                return False
        
        return True
    
    async def process_file(self, file_path: Path) -> Optional[Document]:
        """Process a single file into a Document."""
        try:
            # Read file content
            content = self._read_file_content(file_path)
            if not content:
                self.logger.debug(f"Empty content for file: {file_path}")
                return None
            
            # Generate content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Create document
            document = Document(
                title=file_path.stem,
                content=content,
                source_type="filesystem",
                source_path=str(file_path),
                content_hash=content_hash
            )
            
            return document
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            return None
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content based on file type."""
        try:
            # For now, just handle text files
            if file_path.suffix.lower() in {'.txt', '.md', '.py', '.js', '.cpp', '.h', '.ts'}:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            # TODO: Add handlers for PDF, DOCX, etc.
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {str(e)}")
            return None