"""Configuration management for the second brain stack."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    path: str = Field(default="storage/brain.db", description="Database file path")
    wal_mode: bool = Field(default=True, description="Enable WAL mode for better concurrency")
    fts_enabled: bool = Field(default=True, description="Enable FTS5 full-text search")
    vector_extension: str = Field(default="sqlite-vec", description="Vector extension to use")
    pool_size: int = Field(default=10, description="Connection pool size")
    

class ServiceConfig(BaseSettings):
    """Individual service configuration."""
    
    port: int
    host: str = "0.0.0.0"
    workers: int = 1
    debug: bool = False
    batch_size: Optional[int] = None
    max_file_size: Optional[str] = None
    embedding_model: Optional[str] = None
    vector_dimensions: Optional[int] = None
    similarity_threshold: Optional[float] = None
    entity_model: Optional[str] = None
    min_confidence: Optional[float] = None
    context_window: Optional[int] = None
    memory_turns: Optional[int] = None


class ServicesConfig(BaseSettings):
    """All services configuration."""
    
    ingestion: ServiceConfig = ServiceConfig(port=8001, workers=4)
    search: ServiceConfig = ServiceConfig(port=8002)
    knowledge: ServiceConfig = ServiceConfig(port=8003)
    chat: ServiceConfig = ServiceConfig(port=8004)
    gateway: ServiceConfig = ServiceConfig(port=8000)


class EmbeddingsConfig(BaseSettings):
    """Embeddings configuration."""
    
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings"
    )
    model_path: str = Field(default="storage/models/", description="Local model cache path")
    cache_size: int = Field(default=1000, description="Number of cached embeddings")
    batch_size: int = Field(default=32, description="Batch size for embedding generation")
    vector_dimensions: int = Field(default=384, description="Vector dimensions")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold for matches")
    device: str = Field(default="cpu", description="Device to use (cpu/cuda)")


class KnowledgeConfig(BaseSettings):
    """Knowledge graph configuration."""
    
    entity_model: str = Field(default="en_core_web_sm", description="spaCy model for NER")
    min_confidence: float = Field(default=0.8, description="Minimum confidence for entities")
    max_entities_per_doc: int = Field(default=100, description="Maximum entities per document")
    relationship_types: List[str] = Field(
        default=[
            "RELATED_TO", "CONTAINS", "PART_OF", "MENTIONED_IN", 
            "AUTHORED_BY", "CREATED_ON", "REFERENCES"
        ],
        description="Supported relationship types"
    )


class ConnectorsConfig(BaseSettings):
    """Data connectors configuration."""
    
    supported_file_types: List[str] = Field(
        default=[".txt", ".md", ".pdf", ".docx", ".py", ".cpp", ".h", ".js", ".ts"],
        description="Supported file extensions"
    )
    ignore_patterns: List[str] = Field(
        default=["*.pyc", "__pycache__", ".git", "node_modules", ".env"],
        description="Patterns to ignore during ingestion"
    )
    max_file_size: str = Field(default="50MB", description="Maximum file size to process")
    batch_size: int = Field(default=100, description="Batch size for processing")
    
    # Nested configs with flexible structure
    filesystem: Optional[dict] = None
    web: Optional[dict] = None
    git: Optional[dict] = None


class InterfacesConfig(BaseSettings):
    """User interfaces configuration."""
    
    cli_pager: str = Field(default="less", description="CLI pager command")
    cli_editor: str = Field(default="$EDITOR", description="CLI editor command")
    cli_colors: bool = Field(default=True, description="Enable CLI colors")
    
    web_template_dir: str = Field(default="interfaces/web/templates", description="Web templates directory")
    web_static_dir: str = Field(default="interfaces/web/static", description="Web static files directory")
    web_debug: bool = Field(default=False, description="Enable web debug mode")
    
    # Nested configs with flexible structure
    cli: Optional[dict] = None
    web: Optional[dict] = None


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    file_path: Optional[str] = Field(default=None, description="Log file path")
    structured: bool = Field(default=True, description="Use structured logging")


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
    
    # Core settings
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development/production)")
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Secret key")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    interfaces: InterfacesConfig = Field(default_factory=InterfacesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Data directories
    data_dir: str = Field(default="storage", description="Main data directory")
    cache_dir: str = Field(default="storage/cache", description="Cache directory")
    backup_dir: str = Field(default="storage/backups", description="Backup directory")
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """Load settings from a YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            return cls()
            
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            
        return cls(**config_data)
    
    def create_directories(self) -> None:
        """Create necessary directories."""
        dirs_to_create = [
            self.data_dir,
            self.cache_dir, 
            self.backup_dir,
            Path(self.database.path).parent,
            self.embeddings.model_path,
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    # Try to load from brain.yml first, then environment variables
    config_files = ["brain.yml", "config.yml"]
    
    for config_file in config_files:
        if Path(config_file).exists():
            return Settings.from_yaml(config_file)
    
    return Settings()


# Global settings instance
settings = get_settings()