"""Filesystem scanner for document ingestion."""

import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional, Set

from core.database.models import Document
from core.utils import get_logger, settings


class FilesystemScanner:
    """Scans filesystem for documents to ingest."""
    
    def __init__(self, supported_types: Optional[List[str]] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.supported_types = set(supported_types or settings.connectors.supported_file_types)
        self.ignore_patterns = set(settings.connectors.ignore_patterns)
        
        self.logger.info(
            "FilesystemScanner initialized",
            supported_types=list(self.supported_types),
            ignore_patterns=list(self.ignore_patterns)
        )
    
    async def scan_directory(self, directory: Path, recursive: bool = True) -> List[Path]:
        """Scan directory for supported files."""
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        files = []
        pattern = "**/*" if recursive else "*"
        
        try:
            for file_path in directory.glob(pattern):
                if self._should_process_file(file_path):
                    files.append(file_path)
            
            self.logger.info(
                "Directory scan completed",
                directory=str(directory),
                recursive=recursive,
                files_found=len(files)
            )
            
            return files
            
        except Exception as e:
            self.logger.error(
                "Directory scan failed",
                directory=str(directory),
                error=str(e)
            )
            raise
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        # Skip directories
        if file_path.is_dir():
            return False
        
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if file_path.match(pattern):
                return False
        
        # Check file extension
        if file_path.suffix.lower() not in self.supported_types:
            return False
        
        # Check file size (basic check)
        try:
            # Convert max size from string like "50MB" to bytes
            max_size_str = settings.connectors.max_file_size
            max_size = self._parse_size_string(max_size_str)
            
            if file_path.stat().st_size > max_size:
                self.logger.warning(
                    "File too large, skipping",
                    file=str(file_path),
                    size=file_path.stat().st_size,
                    max_size=max_size
                )
                return False
        except Exception as e:
            self.logger.warning(
                "Could not check file size",
                file=str(file_path),
                error=str(e)
            )
        
        return True
    
    def _parse_size_string(self, size_str: str) -> int:
        """Parse size string like '50MB' to bytes."""
        size_str = size_str.upper().strip()
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    number = float(size_str[:-len(suffix)])
                    return int(number * multiplier)
                except ValueError:
                    break
        
        # Default to parsing as plain number (bytes)
        try:
            return int(size_str)
        except ValueError:
            return 50 * 1024 * 1024  # Default 50MB
    
    async def process_file(self, file_path: Path) -> Optional[Document]:
        """Process a single file and create Document."""
        try:
            # Read file content
            content = await self._read_file_content(file_path)
            if not content.strip():
                self.logger.debug("Empty file, skipping", file=str(file_path))
                return None
            
            # Generate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Extract title (use filename without extension as title)
            title = file_path.stem
            
            # Get file metadata
            stat = file_path.stat()
            metadata = {
                'file_size': stat.st_size,
                'modified_time': stat.st_mtime,
                'mime_type': mimetypes.guess_type(str(file_path))[0],
                'extension': file_path.suffix.lower(),
                'directory': str(file_path.parent),
            }
            
            # Create document
            document = Document(
                title=title,
                content=content,
                source_type="filesystem",
                source_path=str(file_path.resolve()),
                content_hash=content_hash,
                word_count=len(content.split()),
                doc_metadata=str(metadata),  # JSON string
            )
            
            self.logger.debug(
                "Document created from file",
                file=str(file_path),
                title=title,
                content_length=len(content),
                word_count=document.word_count
            )
            
            return document
            
        except Exception as e:
            self.logger.error(
                "Failed to process file",
                file=str(file_path),
                error=str(e)
            )
            return None
    
    async def _read_file_content(self, file_path: Path) -> str:
        """Read file content with appropriate encoding detection."""
        # Try different encodings
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                self.logger.debug(
                    "File read successfully",
                    file=str(file_path),
                    encoding=encoding,
                    length=len(content)
                )
                
                return content
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.logger.error(
                    "Failed to read file",
                    file=str(file_path),
                    encoding=encoding,
                    error=str(e)
                )
                continue
        
        # If all encodings fail, try binary mode and decode with errors='ignore'
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                content = raw_content.decode('utf-8', errors='ignore')
            
            self.logger.warning(
                "File read with error handling",
                file=str(file_path),
                original_size=len(raw_content),
                decoded_size=len(content)
            )
            
            return content
            
        except Exception as e:
            self.logger.error(
                "Failed to read file in any encoding",
                file=str(file_path),
                error=str(e)
            )
            raise
    
    async def get_file_stats(self, directory: Path) -> dict:
        """Get statistics about files in directory."""
        if not directory.exists():
            return {}
        
        stats = {
            'total_files': 0,
            'processable_files': 0,
            'total_size': 0,
            'by_extension': {},
            'by_size_range': {'small': 0, 'medium': 0, 'large': 0},
        }
        
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    stats['total_files'] += 1
                    file_size = file_path.stat().st_size
                    stats['total_size'] += file_size
                    
                    # Count by extension
                    ext = file_path.suffix.lower()
                    stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1
                    
                    # Count by size range
                    if file_size < 1024 * 1024:  # < 1MB
                        stats['by_size_range']['small'] += 1
                    elif file_size < 10 * 1024 * 1024:  # < 10MB
                        stats['by_size_range']['medium'] += 1
                    else:
                        stats['by_size_range']['large'] += 1
                    
                    # Check if processable
                    if self._should_process_file(file_path):
                        stats['processable_files'] += 1
        
        except Exception as e:
            self.logger.error(
                "Failed to get directory stats",
                directory=str(directory),
                error=str(e)
            )
        
        return stats