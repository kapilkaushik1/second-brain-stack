"""Unit tests for configuration system."""

import pytest
from pathlib import Path
import tempfile
import yaml

from core.utils.config import Settings, DatabaseConfig, ServicesConfig, EmbeddingsConfig


class TestDatabaseConfig:
    """Test database configuration."""
    
    def test_database_config_defaults(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        
        assert config.path == "storage/brain.db"
        assert config.wal_mode is True
        assert config.fts_enabled is True
        assert config.vector_extension == "sqlite-vec"
        assert config.pool_size == 10
    
    def test_database_config_custom(self):
        """Test custom database configuration."""
        config = DatabaseConfig(
            path="/custom/path/brain.db",
            wal_mode=False,
            fts_enabled=False,
            pool_size=5
        )
        
        assert config.path == "/custom/path/brain.db"
        assert config.wal_mode is False
        assert config.fts_enabled is False
        assert config.pool_size == 5


class TestServicesConfig:
    """Test services configuration."""
    
    def test_services_config_defaults(self):
        """Test default services configuration."""
        config = ServicesConfig()
        
        assert config.ingestion.port == 8001
        assert config.ingestion.workers == 4
        assert config.search.port == 8002
        assert config.knowledge.port == 8003
        assert config.chat.port == 8004
        assert config.gateway.port == 8000


class TestEmbeddingsConfig:
    """Test embeddings configuration."""
    
    def test_embeddings_config_defaults(self):
        """Test default embeddings configuration."""
        config = EmbeddingsConfig()
        
        assert config.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.model_path == "storage/models/"
        assert config.cache_size == 1000
        assert config.batch_size == 32
        assert config.vector_dimensions == 384
        assert config.similarity_threshold == 0.7
        assert config.device == "cpu"


class TestSettings:
    """Test main settings class."""
    
    def test_settings_defaults(self):
        """Test default settings."""
        settings = Settings()
        
        assert settings.debug is False
        assert settings.environment == "development"
        assert settings.data_dir == "storage"
        assert settings.cache_dir == "storage/cache"
        assert settings.backup_dir == "storage/backups"
        
        # Test nested configs
        assert settings.database.path == "storage/brain.db"
        assert settings.embeddings.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.services.ingestion.port == 8001
    
    def test_settings_from_yaml(self, temp_dir):
        """Test loading settings from YAML file."""
        config_data = {
            "debug": True,
            "environment": "testing",
            "database": {
                "path": "test_brain.db",
                "wal_mode": False
            },
            "embeddings": {
                "model_name": "custom-model",
                "cache_size": 500
            },
            "services": {
                "ingestion": {
                    "port": 9001,
                    "workers": 2
                }
            }
        }
        
        config_file = temp_dir / "test_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        settings = Settings.from_yaml(str(config_file))
        
        assert settings.debug is True
        assert settings.environment == "testing"
        assert settings.database.path == "test_brain.db"
        assert settings.database.wal_mode is False
        assert settings.embeddings.model_name == "custom-model"
        assert settings.embeddings.cache_size == 500
        assert settings.services.ingestion.port == 9001
        assert settings.services.ingestion.workers == 2
    
    def test_settings_from_nonexistent_yaml(self):
        """Test loading from non-existent YAML file."""
        settings = Settings.from_yaml("nonexistent.yml")
        
        # Should return default settings
        assert settings.debug is False
        assert settings.database.path == "storage/brain.db"
    
    def test_create_directories(self, temp_dir):
        """Test directory creation."""
        # Create settings with custom paths
        settings = Settings()
        settings.data_dir = str(temp_dir / "custom_data")
        settings.cache_dir = str(temp_dir / "custom_cache")
        settings.backup_dir = str(temp_dir / "custom_backups")
        settings.database.path = str(temp_dir / "db" / "brain.db")
        settings.embeddings.model_path = str(temp_dir / "models")
        
        # Create directories
        settings.create_directories()
        
        # Verify directories exist
        assert Path(settings.data_dir).exists()
        assert Path(settings.cache_dir).exists()
        assert Path(settings.backup_dir).exists()
        assert Path(settings.database.path).parent.exists()
        assert Path(settings.embeddings.model_path).exists()
    
    def test_environment_variable_override(self, monkeypatch):
        """Test environment variable overrides."""
        # Set environment variables
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE__PATH", "/env/brain.db")
        monkeypatch.setenv("SERVICES__INGESTION__PORT", "9001")
        
        settings = Settings()
        
        assert settings.debug is True
        assert settings.environment == "production"
        assert settings.database.path == "/env/brain.db"
        assert settings.services.ingestion.port == 9001
    
    def test_nested_config_validation(self):
        """Test validation of nested configurations."""
        # This should work
        settings = Settings()
        settings.embeddings.similarity_threshold = 0.5
        assert settings.embeddings.similarity_threshold == 0.5
        
        # Test that pydantic validation still works
        with pytest.raises(ValueError):
            settings.embeddings.cache_size = -1  # Should be positive
    
    def test_yaml_with_invalid_structure(self, temp_dir):
        """Test YAML with invalid structure."""
        invalid_config = {
            "database": "this should be an object, not a string"
        }
        
        config_file = temp_dir / "invalid_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        # Should raise validation error
        with pytest.raises(ValueError):
            Settings.from_yaml(str(config_file))