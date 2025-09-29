"""Knowledge Graph Service for Second Brain Stack."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from core.database import DatabaseManager
from core.utils import get_logger

app = FastAPI(title="Second Brain Knowledge Service", version="1.0.0")
logger = get_logger(__name__)

# Global state
db_manager = None


class EntityResponse(BaseModel):
    id: int
    name: str
    entity_type: str
    confidence: float
    first_seen: str


class RelationshipResponse(BaseModel):
    id: int
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float


@app.on_event("startup")
async def startup_event():
    """Initialize the knowledge service."""
    global db_manager
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/brain.db")
    db_manager = DatabaseManager(database_url)
    
    logger.info("Knowledge service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "knowledge"}


@app.get("/entities", response_model=List[EntityResponse])
async def get_entities(
    limit: int = 50,
    offset: int = 0,
    entity_type: Optional[str] = None
):
    """Get entities from the knowledge graph."""
    try:
        entities = await db_manager.get_entities(limit=limit, offset=offset)
        
        response = []
        for entity in entities:
            if entity_type is None or entity.entity_type == entity_type:
                response.append(EntityResponse(
                    id=entity.id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    confidence=entity.confidence,
                    first_seen=entity.first_seen.isoformat()
                ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error: {str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get entities: {str(e)}")


@app.get("/relationships", response_model=List[RelationshipResponse])
async def get_relationships(limit: int = 50, offset: int = 0):
    """Get relationships from the knowledge graph."""
    try:
        relationships = await db_manager.get_relationships(limit=limit, offset=offset)
        
        response = []
        for rel in relationships:
            # Get entity names
            source_entity = await db_manager.get_entity_by_id(rel.source_entity_id)
            target_entity = await db_manager.get_entity_by_id(rel.target_entity_id)
            
            if source_entity and target_entity:
                response.append(RelationshipResponse(
                    id=rel.id,
                    source_entity=source_entity.name,
                    target_entity=target_entity.name,
                    relation_type=rel.relation_type,
                    confidence=rel.confidence
                ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error: {str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get relationships: {str(e)}")


@app.get("/graph")
async def get_knowledge_graph(
    center_entity: Optional[str] = None,
    max_depth: int = 2,
    limit: int = 100
):
    """Get knowledge graph data for visualization."""
    try:
        # Get entities and relationships
        entities = await db_manager.get_entities(limit=limit)
        relationships = await db_manager.get_relationships(limit=limit)
        
        # Convert to graph format
        nodes = []
        edges = []
        
        # Create entity nodes
        entity_map = {}
        for entity in entities:
            node = {
                "id": str(entity.id),
                "label": entity.name,
                "type": entity.entity_type,
                "confidence": entity.confidence
            }
            nodes.append(node)
            entity_map[entity.id] = entity.name
        
        # Create relationship edges
        for rel in relationships:
            if rel.source_entity_id in entity_map and rel.target_entity_id in entity_map:
                edge = {
                    "source": str(rel.source_entity_id),
                    "target": str(rel.target_entity_id),
                    "label": rel.relation_type,
                    "confidence": rel.confidence
                }
                edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_entities": len(nodes),
                "total_relationships": len(edges)
            }
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge graph: {str(e)}")


@app.get("/stats")
async def get_knowledge_stats():
    """Get knowledge graph statistics."""
    try:
        stats = await db_manager.get_stats()
        
        return {
            "entities": stats["entities"],
            "relationships": stats["relationships"],
            "documents": stats["documents"]
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)