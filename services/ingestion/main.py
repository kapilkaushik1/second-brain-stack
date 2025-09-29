"""Ingestion service main application."""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from core.database import DatabaseManager, Document
from core.embeddings import EmbeddingGenerator
from core.utils import get_logger, settings
from connectors.filesystem import FilesystemScanner


logger = get_logger("IngestionService")


# Pydantic models for API
class IngestionRequest(BaseModel):
    source_type: str
    source_path: str
    recursive: bool = True
    file_types: Optional[List[str]] = None


class IngestionResponse(BaseModel):
    task_id: str
    message: str


class IngestionStatus(BaseModel):
    task_id: str
    status: str
    processed_files: int
    total_files: int
    errors: List[str] = []


# Global state
db_manager: DatabaseManager = None
embedding_generator: EmbeddingGenerator = None
ingestion_tasks = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events."""
    global db_manager, embedding_generator
    
    logger.info("Starting Ingestion Service")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.create_tables()
    
    # Initialize embedding generator
    embedding_generator = EmbeddingGenerator()
    embedding_generator.warmup()
    
    logger.info("Ingestion Service started successfully")
    
    yield
    
    logger.info("Shutting down Ingestion Service")


app = FastAPI(
    title="Second Brain Ingestion Service",
    description="Document ingestion and processing service",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ingestion",
        "version": "0.1.0"
    }


@app.post("/ingest", response_model=IngestionResponse)
async def start_ingestion(request: IngestionRequest, background_tasks: BackgroundTasks):
    """Start document ingestion process."""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    logger.info(
        "Starting ingestion task",
        task_id=task_id,
        source_type=request.source_type,
        source_path=request.source_path
    )
    
    # Initialize task status
    ingestion_tasks[task_id] = IngestionStatus(
        task_id=task_id,
        status="started",
        processed_files=0,
        total_files=0
    )
    
    # Start background task
    background_tasks.add_task(
        process_ingestion,
        task_id,
        request
    )
    
    return IngestionResponse(
        task_id=task_id,
        message="Ingestion task started"
    )


@app.post("/documents")
async def create_document_endpoint():
    """Create document endpoint for compatibility."""
    return {"message": "Use /ingest endpoint instead", "status": "deprecated"}

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of ingestion task - alias for compatibility."""
    return await get_ingestion_status(task_id)


@app.get("/ingest/{task_id}/cancel")
async def cancel_ingestion(task_id: str):
    """Cancel ingestion task."""
    if task_id not in ingestion_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Set status to cancelled
    ingestion_tasks[task_id].status = "cancelled"
    
    logger.info("Ingestion task cancelled", task_id=task_id)
    
    return {"message": "Task cancelled"}


@app.get("/stats")
async def get_ingestion_stats():
    """Get ingestion statistics."""
    stats = await db_manager.get_stats()
    
    return {
        "database_stats": stats,
        "active_tasks": len([t for t in ingestion_tasks.values() if t.status == "processing"]),
        "completed_tasks": len([t for t in ingestion_tasks.values() if t.status == "completed"]),
        "failed_tasks": len([t for t in ingestion_tasks.values() if t.status == "failed"]),
        "embedding_model": embedding_generator.model_name,
        "embedding_cache_size": len(embedding_generator._cache),
    }


async def process_ingestion(task_id: str, request: IngestionRequest):
    """Process ingestion in background."""
    task_status = ingestion_tasks[task_id]
    
    try:
        task_status.status = "processing"
        
        if request.source_type == "filesystem":
            await process_filesystem_ingestion(task_id, request)
        else:
            task_status.errors.append(f"Unsupported source type: {request.source_type}")
            task_status.status = "failed"
            return
        
        task_status.status = "completed"
        logger.info("Ingestion task completed", task_id=task_id)
        
    except Exception as e:
        task_status.status = "failed"
        task_status.errors.append(str(e))
        logger.error(
            "Ingestion task failed",
            task_id=task_id,
            error=str(e)
        )


async def process_filesystem_ingestion(task_id: str, request: IngestionRequest):
    """Process filesystem ingestion."""
    from pathlib import Path
    
    task_status = ingestion_tasks[task_id]
    scanner = FilesystemScanner(supported_types=request.file_types)
    
    try:
        # Scan for files
        source_path = Path(request.source_path)
        files = await scanner.scan_directory(source_path, request.recursive)
        
        task_status.total_files = len(files)
        logger.info(
            "Files discovered",
            task_id=task_id,
            total_files=len(files)
        )
        
        # Process files in batches
        batch_size = settings.connectors.batch_size
        
        for i in range(0, len(files), batch_size):
            # Check if task was cancelled
            if task_status.status == "cancelled":
                logger.info("Task was cancelled", task_id=task_id)
                return
            
            batch = files[i:i + batch_size]
            await process_file_batch(task_id, scanner, batch)
        
        logger.info(
            "Filesystem ingestion completed",
            task_id=task_id,
            processed_files=task_status.processed_files,
            total_files=task_status.total_files
        )
        
    except Exception as e:
        logger.error(
            "Filesystem ingestion failed",
            task_id=task_id,
            error=str(e)
        )
        raise


async def process_file_batch(task_id: str, scanner: FilesystemScanner, files: List):
    """Process a batch of files."""
    task_status = ingestion_tasks[task_id]
    
    for file_path in files:
        try:
            # Check if task was cancelled
            if task_status.status == "cancelled":
                return
            
            # Process file
            document = await scanner.process_file(file_path)
            
            if document:
                # Check if document already exists (by content hash)
                existing = await db_manager.get_document_by_hash(document.content_hash)
                
                if existing:
                    logger.debug(
                        "Document already exists, skipping",
                        file=str(file_path),
                        content_hash=document.content_hash
                    )
                else:
                    # Create document
                    created_doc = await db_manager.create_document(document)
                    
                    # Generate and store embedding
                    await generate_document_embedding(created_doc)
                    
                    logger.debug(
                        "Document processed successfully",
                        document_id=created_doc.id,
                        file=str(file_path)
                    )
            
            task_status.processed_files += 1
            
        except Exception as e:
            error_msg = f"Failed to process {file_path}: {str(e)}"
            task_status.errors.append(error_msg)
            logger.error(
                "File processing failed",
                file=str(file_path),
                error=str(e)
            )


async def generate_document_embedding(document: Document):
    """Generate and store embedding for document."""
    try:
        # Generate embedding
        embedding = embedding_generator.encode_document(
            title=document.title,
            content=document.content
        )
        
        # Store embedding
        await db_manager.update_document_embedding(document.id, embedding)
        
        logger.debug(
            "Embedding generated",
            document_id=document.id,
            embedding_shape=embedding.shape
        )
        
    except Exception as e:
        logger.error(
            "Failed to generate embedding",
            document_id=document.id,
            error=str(e)
        )


def main():
    """Run the ingestion service."""
    port = settings.services.ingestion.port
    workers = settings.services.ingestion.workers
    
    logger.info(
        "Starting Ingestion Service",
        port=port,
        workers=workers,
        debug=settings.debug
    )
    
    uvicorn.run(
        "services.ingestion.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,  # Use 1 worker for simplicity with global state
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )


if __name__ == "__main__":
    main()