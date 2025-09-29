"""Shared utilities for the Second Brain Stack."""

import logging
from typing import Any

def get_logger(name):
    return logging.getLogger(name)

class Settings:
    def __init__(self):
        self.debug = False
        self.connectors = ConnectorSettings()
        self.services = ServiceSettings()

class ConnectorSettings:
    def __init__(self):
        self.batch_size = 10

class ServiceSettings:
    def __init__(self):
        self.ingestion = IngestionServiceSettings()

class IngestionServiceSettings:
    def __init__(self):
        self.port = 8001
        self.workers = 1

settings = Settings()

__all__ = ["get_logger", "settings"]