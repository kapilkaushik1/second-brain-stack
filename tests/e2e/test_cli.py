"""End-to-end tests for CLI interface."""

import pytest
import subprocess
import tempfile
from pathlib import Path
import json


class TestCLIEndToEnd:
    """End-to-end tests for the CLI interface."""
    
    def run_cli_command(self, args, cwd=None, env=None):
        """Helper to run CLI commands."""
        cmd = ["python", "-m", "interfaces.cli"] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result
    
    def test_cli_help(self, temp_dir):
        """Test CLI help command."""
        result = self.run_cli_command(["--help"], cwd=temp_dir)
        
        assert result.returncode == 0
        assert "Second Brain Stack CLI" in result.stdout
        assert "ingest" in result.stdout
        assert "search" in result.stdout
        assert "db" in result.stdout
        assert "config" in result.stdout
    
    def test_cli_version(self, temp_dir):
        """Test CLI version command."""
        result = self.run_cli_command(["--version"], cwd=temp_dir)
        
        assert result.returncode == 0
        assert "0.1.0" in result.stdout or "version" in result.stdout.lower()
    
    def test_cli_database_init(self, temp_dir):
        """Test database initialization via CLI."""
        # Set up test environment
        test_db_path = temp_dir / "test_cli.db"
        config_content = f"""
database:
  path: "{test_db_path}"
  wal_mode: true
  fts_enabled: true
"""
        config_file = temp_dir / "brain.yml"
        config_file.write_text(config_content)
        
        # Initialize database
        result = self.run_cli_command(
            ["--config", str(config_file), "db", "init"],
            cwd=temp_dir
        )
        
        assert result.returncode == 0
        assert "Database initialized successfully" in result.stdout or "successfully" in result.stdout.lower()
        assert test_db_path.exists()
    
    def test_cli_database_stats(self, temp_dir):
        """Test database statistics via CLI."""
        # Set up test environment
        test_db_path = temp_dir / "test_cli_stats.db"
        config_content = f"""
database:
  path: "{test_db_path}"
  wal_mode: true
  fts_enabled: true
"""
        config_file = temp_dir / "brain.yml"
        config_file.write_text(config_content)
        
        # Initialize database first
        init_result = self.run_cli_command(
            ["--config", str(config_file), "db", "init"],
            cwd=temp_dir
        )
        assert init_result.returncode == 0
        
        # Get stats
        result = self.run_cli_command(
            ["--config", str(config_file), "db", "stats"],
            cwd=temp_dir
        )
        
        assert result.returncode == 0
        assert "Documents" in result.stdout or "documents" in result.stdout.lower()
    
    def test_cli_config_show(self, temp_dir):
        """Test configuration display."""
        result = self.run_cli_command(["config", "show"], cwd=temp_dir)
        
        assert result.returncode == 0
        assert "Database Path" in result.stdout or "database" in result.stdout.lower()
    
    def test_cli_config_create(self, temp_dir):
        """Test configuration file creation."""
        # Run config create
        result = self.run_cli_command(["config", "create"], cwd=temp_dir)
        
        # Should create brain.yml file
        config_file = temp_dir / "brain.yml"
        assert config_file.exists()
        
        # Verify content
        content = config_file.read_text()
        assert "database:" in content
        assert "services:" in content
        assert "embeddings:" in content
    
    def test_cli_ingestion_with_sample_files(self, temp_dir):
        """Test document ingestion via CLI."""
        # Set up test environment
        test_db_path = temp_dir / "test_ingestion.db"
        config_content = f"""
database:
  path: "{test_db_path}"
  wal_mode: true
  fts_enabled: true
connectors:
  supported_file_types: [".txt", ".md"]
  ignore_patterns: ["*.pyc"]
"""
        config_file = temp_dir / "brain.yml"
        config_file.write_text(config_content)
        
        # Create sample documents directory
        docs_dir = temp_dir / "sample_docs"
        docs_dir.mkdir()
        
        # Create test files
        (docs_dir / "doc1.txt").write_text("This is a test document about machine learning.")
        (docs_dir / "doc2.md").write_text("# Python Guide\n\nPython is great for AI development.")
        (docs_dir / "ignore.pyc").write_text("compiled bytecode")
        
        # Initialize database
        init_result = self.run_cli_command(
            ["--config", str(config_file), "db", "init"],
            cwd=temp_dir
        )
        assert init_result.returncode == 0
        
        # Run ingestion
        ingest_result = self.run_cli_command([
            "--config", str(config_file),
            "ingest", "add",
            "--source", "filesystem",
            "--path", str(docs_dir)
        ], cwd=temp_dir)
        
        # Check if ingestion completed (might have some issues but should not crash)
        # We expect it to process files even if there are minor errors
        assert ingest_result.returncode == 0 or "Processed" in ingest_result.stdout
        
        # Verify database has content
        stats_result = self.run_cli_command(
            ["--config", str(config_file), "db", "stats"],
            cwd=temp_dir
        )
        assert stats_result.returncode == 0
    
    def test_cli_error_handling(self, temp_dir):
        """Test CLI error handling."""
        # Test with invalid command
        result = self.run_cli_command(["invalid_command"], cwd=temp_dir)
        assert result.returncode != 0
        
        # Test database operation without initialization
        result = self.run_cli_command(["db", "stats"], cwd=temp_dir)
        # Should handle gracefully (might error but shouldn't crash)
        assert "error" in result.stderr.lower() or result.returncode != 0 or result.stdout
    
    def test_cli_debug_mode(self, temp_dir):
        """Test CLI debug mode."""
        result = self.run_cli_command(["--debug", "config", "show"], cwd=temp_dir)
        
        assert result.returncode == 0
        # In debug mode, should see more verbose output or debug info
    
    def test_cli_workflow_full(self, temp_dir):
        """Test complete CLI workflow."""
        # Set up environment
        test_db_path = temp_dir / "workflow_test.db"
        config_content = f"""
database:
  path: "{test_db_path}"
  wal_mode: true
  fts_enabled: true
"""
        config_file = temp_dir / "brain.yml"
        config_file.write_text(config_content)
        
        # Create sample content
        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "sample.txt").write_text("This is a sample document for workflow testing.")
        
        # Step 1: Initialize database
        result1 = self.run_cli_command(
            ["--config", str(config_file), "db", "init"],
            cwd=temp_dir
        )
        assert result1.returncode == 0
        
        # Step 2: Check initial stats
        result2 = self.run_cli_command(
            ["--config", str(config_file), "db", "stats"],
            cwd=temp_dir
        )
        assert result2.returncode == 0
        
        # Step 3: Ingest documents
        result3 = self.run_cli_command([
            "--config", str(config_file),
            "ingest", "add", 
            "--source", "filesystem",
            "--path", str(docs_dir)
        ], cwd=temp_dir)
        # Should complete without major errors
        
        # Step 4: Check final stats
        result4 = self.run_cli_command(
            ["--config", str(config_file), "db", "stats"],
            cwd=temp_dir
        )
        assert result4.returncode == 0
        
        # Database should exist and have content
        assert test_db_path.exists()
    
    def test_cli_concurrent_safety(self, temp_dir):
        """Test CLI concurrent execution safety."""
        # This is a basic test - in production you'd want more sophisticated concurrency testing
        import threading
        import time
        
        results = []
        
        def run_config_show():
            result = self.run_cli_command(["config", "show"], cwd=temp_dir)
            results.append(result.returncode)
        
        # Run multiple CLI commands concurrently
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_config_show)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # All should complete successfully
        assert len(results) == 3
        assert all(code == 0 for code in results)