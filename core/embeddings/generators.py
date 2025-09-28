"""Embedding generation using sentence transformers."""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from core.utils import get_logger, settings


class EmbeddingGenerator:
    """Handles embedding generation and caching."""
    
    def __init__(self, model_name: Optional[str] = None, cache_size: int = 1000):
        self.logger = get_logger(self.__class__.__name__)
        self.model_name = model_name or settings.embeddings.model_name
        self.cache_size = cache_size
        self.device = settings.embeddings.device
        
        # Initialize model
        self.model = self._load_model()
        
        # Embedding cache
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_order: List[str] = []
        
        self.logger.info(
            "EmbeddingGenerator initialized",
            model_name=self.model_name,
            device=self.device,
            vector_dimensions=self.model.get_sentence_embedding_dimension()
        )
    
    def _load_model(self) -> SentenceTransformer:
        """Load sentence transformer model."""
        try:
            # Use local cache directory
            cache_dir = Path(settings.embeddings.model_path)
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            model = SentenceTransformer(
                self.model_name,
                cache_folder=str(cache_dir),
                device=self.device
            )
            
            self.logger.info(
                "Model loaded successfully",
                model_name=self.model_name,
                dimensions=model.get_sentence_embedding_dimension()
            )
            
            return model
            
        except Exception as e:
            self.logger.error(
                "Failed to load model",
                model_name=self.model_name,
                error=str(e)
            )
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _add_to_cache(self, key: str, embedding: np.ndarray) -> None:
        """Add embedding to cache with LRU eviction."""
        if key in self._cache:
            # Move to end (most recent)
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return
        
        # Add new entry
        self._cache[key] = embedding
        self._cache_order.append(key)
        
        # Evict oldest if cache is full
        if len(self._cache) > self.cache_size:
            oldest_key = self._cache_order.pop(0)
            del self._cache[oldest_key]
    
    def _get_from_cache(self, key: str) -> Optional[np.ndarray]:
        """Get embedding from cache."""
        if key in self._cache:
            # Move to end (most recent)
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return self._cache[key]
        return None
    
    def encode_single(self, text: str, use_cache: bool = True) -> np.ndarray:
        """Generate embedding for single text."""
        if not text.strip():
            return np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(text)
            cached_embedding = self._get_from_cache(cache_key)
            if cached_embedding is not None:
                return cached_embedding
        
        # Generate embedding
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            ).astype(np.float32)
            
            # Cache result
            if use_cache:
                self._add_to_cache(cache_key, embedding)
            
            self.logger.debug(
                "Embedding generated",
                text_length=len(text),
                embedding_shape=embedding.shape
            )
            
            return embedding
            
        except Exception as e:
            self.logger.error(
                "Failed to generate embedding",
                text_preview=text[:100] + "..." if len(text) > 100 else text,
                error=str(e)
            )
            # Return zero vector as fallback
            return np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)
    
    def encode_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        use_cache: bool = True,
        show_progress: bool = False
    ) -> List[np.ndarray]:
        """Generate embeddings for batch of texts."""
        if not texts:
            return []
        
        batch_size = batch_size or settings.embeddings.batch_size
        embeddings = []
        
        # Process texts and check cache
        texts_to_process = []
        indices_to_process = []
        
        for i, text in enumerate(texts):
            if not text.strip():
                embeddings.append(
                    np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)
                )
                continue
            
            if use_cache:
                cache_key = self._get_cache_key(text)
                cached_embedding = self._get_from_cache(cache_key)
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                    continue
            
            # Need to process this text
            texts_to_process.append(text)
            indices_to_process.append(i)
            embeddings.append(None)  # Placeholder
        
        # Process remaining texts in batches
        if texts_to_process:
            try:
                processed_embeddings = self.model.encode(
                    texts_to_process,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=show_progress
                ).astype(np.float32)
                
                # Fill in results and update cache
                for i, (processed_idx, embedding) in enumerate(zip(indices_to_process, processed_embeddings)):
                    embeddings[processed_idx] = embedding
                    
                    if use_cache:
                        cache_key = self._get_cache_key(texts_to_process[i])
                        self._add_to_cache(cache_key, embedding)
                
                self.logger.info(
                    "Batch embeddings generated",
                    total_texts=len(texts),
                    processed_texts=len(texts_to_process),
                    cached_texts=len(texts) - len(texts_to_process)
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to generate batch embeddings",
                    batch_size=len(texts_to_process),
                    error=str(e)
                )
                # Fill remaining with zero vectors
                zero_vector = np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)
                for processed_idx in indices_to_process:
                    if embeddings[processed_idx] is None:
                        embeddings[processed_idx] = zero_vector
        
        return embeddings
    
    def encode_document(
        self,
        title: str,
        content: str,
        metadata: Optional[Dict] = None,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> np.ndarray:
        """
        Generate document embedding by combining title, content, and metadata.
        
        For long documents, creates chunks and averages embeddings.
        """
        # Combine text components
        text_parts = []
        
        if title.strip():
            text_parts.append(f"Title: {title}")
        
        if content.strip():
            text_parts.append(f"Content: {content}")
        
        if metadata:
            # Add relevant metadata fields
            for key, value in metadata.items():
                if isinstance(value, str) and value.strip():
                    text_parts.append(f"{key}: {value}")
        
        combined_text = "\n".join(text_parts)
        
        # If text is short enough, encode directly
        if len(combined_text) <= chunk_size:
            return self.encode_single(combined_text)
        
        # For long documents, create chunks and average embeddings
        chunks = self._create_chunks(combined_text, chunk_size, overlap)
        if not chunks:
            return self.encode_single(combined_text[:chunk_size])
        
        # Generate embeddings for all chunks
        chunk_embeddings = self.encode_batch(chunks, use_cache=False)
        
        # Average the embeddings
        if chunk_embeddings:
            avg_embedding = np.mean(chunk_embeddings, axis=0)
            # Renormalize
            norm = np.linalg.norm(avg_embedding)
            if norm > 0:
                avg_embedding = avg_embedding / norm
            return avg_embedding.astype(np.float32)
        
        return self.encode_single(combined_text[:chunk_size])
    
    def _create_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Create overlapping chunks from text."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at word boundaries
            if end < len(text) and not text[end].isspace():
                last_space = chunk.rfind(' ')
                if last_space > start + chunk_size // 2:  # Don't make chunks too small
                    end = start + last_space
                    chunk = text[start:end]
            
            chunks.append(chunk.strip())
            
            if end >= len(text):
                break
            
            # Move start position with overlap
            start = end - overlap
        
        return chunks
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "dimensions": self.model.get_sentence_embedding_dimension(),
            "device": str(self.model.device),
            "max_seq_length": getattr(self.model, "max_seq_length", "unknown"),
            "cache_size": len(self._cache),
            "cache_hits": getattr(self, "_cache_hits", 0),
        }
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()
        self._cache_order.clear()
        self.logger.info("Embedding cache cleared")
    
    def warmup(self, sample_texts: Optional[List[str]] = None) -> None:
        """Warm up the model with sample texts."""
        if sample_texts is None:
            sample_texts = [
                "This is a sample document about machine learning.",
                "Python is a popular programming language for data science.",
                "Knowledge graphs represent entities and their relationships.",
            ]
        
        self.logger.info("Warming up embedding model")
        start_time = __import__('time').time()
        
        _ = self.encode_batch(sample_texts, use_cache=False)
        
        warmup_time = __import__('time').time() - start_time
        self.logger.info(
            "Model warmup completed",
            warmup_time_seconds=round(warmup_time, 2),
            sample_count=len(sample_texts)
        )