"""Structured logging utilities for the second brain stack."""

import logging
import sys
from typing import Any, Dict, Optional

import structlog


def configure_logging(
    level: str = "INFO",
    structured: bool = True,
    file_path: Optional[str] = None
) -> None:
    """Configure structured logging."""
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if structured:
        processors.extend([
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # File logging if specified
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add logging capabilities to classes."""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__name__)
        
    def log_method_call(self, method_name: str, **kwargs: Any) -> None:
        """Log a method call with parameters."""
        self.logger.debug(
            "Method called",
            method=method_name,
            class_name=self.__class__.__name__,
            **kwargs
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with context."""
        self.logger.error(
            "Error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            class_name=self.__class__.__name__,
            **(context or {})
        )


# Initialize logging with default configuration
configure_logging()