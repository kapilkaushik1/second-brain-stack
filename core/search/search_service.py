"""Search functionality for Second Brain Stack."""

import asyncio
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from core.database import DatabaseManager
from core.database.models import Document
from core.utils import get_logger


class SearchService:
    """Search service for full-text and semantic search."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = get_logger(self.__class__.__name__)
    
    async def search_documents(
        self, 
        query: str, 
        search_type: str = "hybrid",
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search documents with different search types.
        
        Args:
            query: Search query
            search_type: "fulltext", "semantic", or "hybrid" 
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of search results with scores
        """
        try:
            if search_type == "fulltext":
                return await self._fulltext_search(query, limit, offset)
            elif search_type == "semantic":
                return await self._semantic_search(query, limit, offset)
            elif search_type == "hybrid":
                # For now, fall back to fulltext until semantic is fully implemented
                return await self._fulltext_search(query, limit, offset)
            else:
                raise ValueError(f"Unknown search type: {search_type}")
                
        except Exception as e:
            self.logger.error("Search failed", error=str(e), query=query)
            return []
    
    async def _fulltext_search(self, query: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Perform full-text search using SQLite FTS5."""
        try:
            async with self.db_manager.get_session() as session:
                # Simple content-based search for now
                sql_query = text("""
                    SELECT id, title, content, source_type, source_path, created_at,
                           (LENGTH(content) - LENGTH(REPLACE(LOWER(content), LOWER(:query), ''))) / LENGTH(:query) as score
                    FROM document 
                    WHERE LOWER(content) LIKE LOWER(:search_pattern)
                    ORDER BY score DESC, created_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = await session.execute(
                    sql_query,
                    {
                        "query": query,
                        "search_pattern": f"%{query}%",
                        "limit": limit,
                        "offset": offset
                    }
                )
                
                results = []
                for row in result:
                    results.append({
                        "id": row.id,
                        "title": row.title,
                        "content": row.content[:500] + "..." if len(row.content) > 500 else row.content,
                        "source_type": row.source_type,
                        "source_path": row.source_path,
                        "created_at": row.created_at,
                        "score": float(row.score),
                        "search_type": "fulltext"
                    })
                
                self.logger.info("Full-text search completed", 
                               query=query, results_count=len(results))
                return results
                
        except Exception as e:
            self.logger.error("Full-text search failed", error=str(e))
            # Fallback to simple document retrieval
            return await self._simple_search(query, limit, offset)
    
    async def _semantic_search(self, query: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings."""
        # For now, fall back to fulltext search
        # TODO: Implement actual semantic search when embeddings are ready
        self.logger.warning("Semantic search not implemented yet, falling back to fulltext")
        return await self._fulltext_search(query, limit, offset)
    
    async def _simple_search(self, query: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Simple fallback search using basic document retrieval."""
        try:
            # Get documents that contain the query in title or content
            documents = await self.db_manager.get_documents(limit=limit*2, offset=offset)
            
            results = []
            for doc in documents:
                # Simple scoring based on query occurrence
                score = 0.0
                query_lower = query.lower()
                
                if query_lower in doc.title.lower():
                    score += 2.0
                if query_lower in doc.content.lower():
                    score += 1.0
                
                if score > 0:
                    results.append({
                        "id": doc.id,
                        "title": doc.title,
                        "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                        "source_type": doc.source_type,
                        "source_path": doc.source_path,
                        "created_at": doc.created_at,
                        "score": score,
                        "search_type": "simple"
                    })
            
            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)
            
            self.logger.info("Simple search completed", 
                           query=query, results_count=len(results))
            return results[:limit]
            
        except Exception as e:
            self.logger.error("Simple search failed", error=str(e))
            return []