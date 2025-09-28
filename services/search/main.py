"""Search Service for Second Brain Stack."""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import os

from core.database import DatabaseManager
from core.search import SearchService
from core.utils import get_logger

app = FastAPI(title="Second Brain Search Service", version="1.0.0")
logger = get_logger(__name__)

# Global state
db_manager = None
search_service = None


class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"
    limit: int = 10
    offset: int = 0


class SearchResponse(BaseModel):
    query: str
    results: List[dict]
    total_results: int
    search_type: str


@app.on_event("startup")
async def startup_event():
    """Initialize the search service."""
    global db_manager, search_service
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/brain.db")
    db_manager = DatabaseManager(database_url)
    search_service = SearchService(db_manager)
    
    logger.info("Search service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "search"}


@app.get("/search")
async def search_get(
    q: str = Query(..., description="Search query"),
    type: str = Query("hybrid", description="Search type"),
    limit: int = Query(10, description="Maximum results"),
    offset: int = Query(0, description="Results offset")
):
    """Search documents via GET request."""
    try:
        results = await search_service.search_documents(
            query=q,
            search_type=type,
            limit=limit,
            offset=offset
        )
        
        return SearchResponse(
            query=q,
            results=results,
            total_results=len(results),
            search_type=type
        )
        
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_post(request: SearchRequest):
    """Search documents via POST request."""
    try:
        results = await search_service.search_documents(
            query=request.query,
            search_type=request.search_type,
            limit=request.limit,
            offset=request.offset
        )
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_type=request.search_type
        )
        
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/suggest")
async def get_search_suggestions(
    q: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(5, description="Maximum suggestions")
):
    """Get search suggestions based on existing documents."""
    try:
        # Simple suggestion based on document titles
        documents = await db_manager.get_documents(limit=100)
        
        suggestions = []
        query_lower = q.lower()
        
        for doc in documents:
            if query_lower in doc.title.lower():
                suggestions.append({
                    "text": doc.title,
                    "type": "title",
                    "score": 1.0
                })
            elif query_lower in doc.content.lower():
                # Extract a phrase around the match
                content_lower = doc.content.lower()
                index = content_lower.find(query_lower)
                start = max(0, index - 20)
                end = min(len(doc.content), index + len(q) + 20)
                phrase = doc.content[start:end].strip()
                
                suggestions.append({
                    "text": phrase,
                    "type": "content",
                    "score": 0.8
                })
            
            if len(suggestions) >= limit:
                break
        
        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "query": q,
            "suggestions": suggestions[:limit]
        }
        
    except Exception as e:
        logger.error("Suggestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Suggestion failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)