"""Similarity search operations."""

from typing import Dict, List, Tuple, Optional, Union
import numpy as np
from dataclasses import dataclass

from core.utils import get_logger, settings


@dataclass
class SearchResult:
    """Search result with metadata."""
    
    content_id: Union[int, str]
    score: float
    content: str
    metadata: Optional[Dict] = None
    source_type: Optional[str] = None
    

class SimilaritySearch:
    """Handles vector similarity search operations."""
    
    def __init__(self, embedding_dimension: int = 384):
        self.logger = get_logger(self.__class__.__name__)
        self.embedding_dimension = embedding_dimension
        
        # Storage for embeddings and metadata
        self.embeddings: np.ndarray = np.array([]).reshape(0, embedding_dimension)
        self.content_ids: List[Union[int, str]] = []
        self.content_texts: List[str] = []
        self.metadata: List[Dict] = []
        
        self.logger.info(
            "SimilaritySearch initialized",
            embedding_dimension=embedding_dimension
        )
    
    def add_embedding(
        self,
        content_id: Union[int, str],
        embedding: np.ndarray,
        content_text: str = "",
        metadata: Optional[Dict] = None
    ) -> None:
        """Add an embedding to the search index."""
        if embedding.shape[0] != self.embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch. Expected {self.embedding_dimension}, "
                f"got {embedding.shape[0]}"
            )
        
        # Normalize embedding
        normalized_embedding = self._normalize_vector(embedding)
        
        # Add to storage
        if self.embeddings.size == 0:
            self.embeddings = normalized_embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, normalized_embedding])
        
        self.content_ids.append(content_id)
        self.content_texts.append(content_text)
        self.metadata.append(metadata or {})
        
        self.logger.debug(
            "Embedding added to index",
            content_id=content_id,
            total_embeddings=len(self.content_ids)
        )
    
    def add_embeddings_batch(
        self,
        content_ids: List[Union[int, str]],
        embeddings: List[np.ndarray],
        content_texts: Optional[List[str]] = None,
        metadata_list: Optional[List[Dict]] = None
    ) -> None:
        """Add multiple embeddings to the search index."""
        if not content_ids or not embeddings:
            return
        
        if len(content_ids) != len(embeddings):
            raise ValueError("Number of content_ids must match number of embeddings")
        
        content_texts = content_texts or [""] * len(content_ids)
        metadata_list = metadata_list or [{}] * len(content_ids)
        
        if len(content_texts) != len(content_ids):
            raise ValueError("Number of content_texts must match number of content_ids")
        
        if len(metadata_list) != len(content_ids):
            raise ValueError("Number of metadata entries must match number of content_ids")
        
        # Validate and normalize embeddings
        normalized_embeddings = []
        for i, embedding in enumerate(embeddings):
            if embedding.shape[0] != self.embedding_dimension:
                raise ValueError(
                    f"Embedding {i} dimension mismatch. Expected {self.embedding_dimension}, "
                    f"got {embedding.shape[0]}"
                )
            normalized_embeddings.append(self._normalize_vector(embedding))
        
        # Convert to numpy array
        embeddings_array = np.array(normalized_embeddings)
        
        # Add to storage
        if self.embeddings.size == 0:
            self.embeddings = embeddings_array
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings_array])
        
        self.content_ids.extend(content_ids)
        self.content_texts.extend(content_texts)
        self.metadata.extend(metadata_list)
        
        self.logger.info(
            "Batch embeddings added to index",
            batch_size=len(content_ids),
            total_embeddings=len(self.content_ids)
        )
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        threshold: Optional[float] = None,
        filter_metadata: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            filter_metadata: Filter results by metadata fields
            
        Returns:
            List of SearchResult objects sorted by similarity score
        """
        if self.embeddings.size == 0:
            return []
        
        threshold = threshold or settings.embeddings.similarity_threshold
        
        # Normalize query embedding
        normalized_query = self._normalize_vector(query_embedding)
        
        # Calculate cosine similarities
        similarities = np.dot(self.embeddings, normalized_query)
        
        # Apply threshold filter
        valid_indices = np.where(similarities >= threshold)[0]
        
        if len(valid_indices) == 0:
            return []
        
        # Get top-k results
        valid_similarities = similarities[valid_indices]
        sorted_indices = np.argsort(valid_similarities)[::-1]  # Descending order
        
        results = []
        for idx in sorted_indices[:k]:
            original_idx = valid_indices[idx]
            score = valid_similarities[idx]
            
            # Apply metadata filter if specified
            if filter_metadata:
                item_metadata = self.metadata[original_idx]
                if not self._matches_filter(item_metadata, filter_metadata):
                    continue
            
            result = SearchResult(
                content_id=self.content_ids[original_idx],
                score=float(score),
                content=self.content_texts[original_idx],
                metadata=self.metadata[original_idx],
            )
            results.append(result)
        
        self.logger.debug(
            "Similarity search completed",
            query_shape=query_embedding.shape,
            total_candidates=len(self.content_ids),
            threshold=threshold,
            results_returned=len(results)
        )
        
        return results
    
    def search_by_content_id(
        self,
        content_id: Union[int, str],
        k: int = 10,
        threshold: Optional[float] = None,
        exclude_self: bool = True
    ) -> List[SearchResult]:
        """Find similar content to a specific item in the index."""
        try:
            idx = self.content_ids.index(content_id)
            query_embedding = self.embeddings[idx]
            
            results = self.search(query_embedding, k + (1 if exclude_self else 0), threshold)
            
            if exclude_self:
                # Remove the query item itself from results
                results = [r for r in results if r.content_id != content_id][:k]
            
            return results
            
        except ValueError:
            self.logger.warning(
                "Content ID not found in search index",
                content_id=content_id
            )
            return []
    
    def get_embedding(self, content_id: Union[int, str]) -> Optional[np.ndarray]:
        """Get embedding vector for a specific content ID."""
        try:
            idx = self.content_ids.index(content_id)
            return self.embeddings[idx].copy()
        except ValueError:
            return None
    
    def remove_embedding(self, content_id: Union[int, str]) -> bool:
        """Remove an embedding from the index."""
        try:
            idx = self.content_ids.index(content_id)
            
            # Remove from all storage arrays
            self.embeddings = np.delete(self.embeddings, idx, axis=0)
            self.content_ids.pop(idx)
            self.content_texts.pop(idx)
            self.metadata.pop(idx)
            
            self.logger.debug(
                "Embedding removed from index",
                content_id=content_id,
                remaining_embeddings=len(self.content_ids)
            )
            
            return True
            
        except ValueError:
            self.logger.warning(
                "Content ID not found for removal",
                content_id=content_id
            )
            return False
    
    def update_embedding(
        self,
        content_id: Union[int, str],
        new_embedding: np.ndarray,
        new_content_text: Optional[str] = None,
        new_metadata: Optional[Dict] = None
    ) -> bool:
        """Update an existing embedding in the index."""
        try:
            idx = self.content_ids.index(content_id)
            
            # Validate and normalize new embedding
            if new_embedding.shape[0] != self.embedding_dimension:
                raise ValueError(
                    f"Embedding dimension mismatch. Expected {self.embedding_dimension}, "
                    f"got {new_embedding.shape[0]}"
                )
            
            # Update embedding
            self.embeddings[idx] = self._normalize_vector(new_embedding)
            
            # Update text and metadata if provided
            if new_content_text is not None:
                self.content_texts[idx] = new_content_text
            
            if new_metadata is not None:
                self.metadata[idx] = new_metadata
            
            self.logger.debug(
                "Embedding updated in index",
                content_id=content_id
            )
            
            return True
            
        except ValueError:
            self.logger.warning(
                "Content ID not found for update",
                content_id=content_id
            )
            return False
    
    def clear(self) -> None:
        """Clear all embeddings from the index."""
        self.embeddings = np.array([]).reshape(0, self.embedding_dimension)
        self.content_ids.clear()
        self.content_texts.clear()
        self.metadata.clear()
        
        self.logger.info("Search index cleared")
    
    def save_index(self, filepath: str) -> None:
        """Save the search index to disk."""
        import pickle
        from pathlib import Path
        
        index_data = {
            'embeddings': self.embeddings,
            'content_ids': self.content_ids,
            'content_texts': self.content_texts,
            'metadata': self.metadata,
            'embedding_dimension': self.embedding_dimension
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)
        
        self.logger.info(
            "Search index saved",
            filepath=filepath,
            total_embeddings=len(self.content_ids)
        )
    
    def load_index(self, filepath: str) -> None:
        """Load a search index from disk."""
        import pickle
        
        try:
            with open(filepath, 'rb') as f:
                index_data = pickle.load(f)
            
            self.embeddings = index_data['embeddings']
            self.content_ids = index_data['content_ids']
            self.content_texts = index_data['content_texts']
            self.metadata = index_data['metadata']
            
            # Validate dimension compatibility
            if index_data['embedding_dimension'] != self.embedding_dimension:
                self.logger.warning(
                    "Embedding dimension mismatch in loaded index",
                    expected=self.embedding_dimension,
                    loaded=index_data['embedding_dimension']
                )
            
            self.logger.info(
                "Search index loaded",
                filepath=filepath,
                total_embeddings=len(self.content_ids)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to load search index",
                filepath=filepath,
                error=str(e)
            )
            raise
    
    def get_stats(self) -> Dict:
        """Get statistics about the search index."""
        if self.embeddings.size == 0:
            return {
                'total_embeddings': 0,
                'embedding_dimension': self.embedding_dimension,
                'memory_usage_mb': 0
            }
        
        memory_usage = (
            self.embeddings.nbytes +
            sum(len(str(cid).encode()) for cid in self.content_ids) +
            sum(len(text.encode()) for text in self.content_texts) +
            sum(len(str(meta).encode()) for meta in self.metadata)
        ) / (1024 * 1024)  # Convert to MB
        
        return {
            'total_embeddings': len(self.content_ids),
            'embedding_dimension': self.embedding_dimension,
            'memory_usage_mb': round(memory_usage, 2),
            'average_content_length': round(
                sum(len(text) for text in self.content_texts) / len(self.content_texts)
            ) if self.content_texts else 0
        }
    
    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """Normalize a vector to unit length."""
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    def _matches_filter(self, item_metadata: Dict, filter_metadata: Dict) -> bool:
        """Check if item metadata matches filter criteria."""
        for key, value in filter_metadata.items():
            if key not in item_metadata:
                return False
            
            item_value = item_metadata[key]
            
            # Handle different comparison types
            if isinstance(value, dict):
                # Support operators like {'$gte': 0.5}
                for op, op_value in value.items():
                    if op == '$gte' and item_value < op_value:
                        return False
                    elif op == '$lte' and item_value > op_value:
                        return False
                    elif op == '$gt' and item_value <= op_value:
                        return False
                    elif op == '$lt' and item_value >= op_value:
                        return False
                    elif op == '$ne' and item_value == op_value:
                        return False
            elif isinstance(value, (list, tuple)):
                # Check if item value is in the list
                if item_value not in value:
                    return False
            else:
                # Direct equality check
                if item_value != value:
                    return False
        
        return True