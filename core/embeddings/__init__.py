"""Embedding generation and similarity search."""

import numpy as np

class EmbeddingGenerator:
    def __init__(self):
        self.model_name = "mock-embedding-model"
        self._cache = {}
    
    def warmup(self):
        pass
    
    def encode_document(self, title, content):
        # Mock embedding - return random vector
        return np.random.random(384)

__all__ = ["EmbeddingGenerator"]