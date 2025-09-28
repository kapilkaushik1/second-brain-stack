"""Database operations and management."""

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, select

from core.utils import get_logger, settings
from .models import ChatMessage, Document, DocumentEntity, Entity, Relationship, SearchQuery


class DatabaseManager:
    """Database operations manager."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.logger = get_logger(self.__class__.__name__)
        
        if database_url is None:
            db_path = Path(settings.database.path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite+aiosqlite:///{db_path}"
        
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
    async def create_tables(self) -> None:
        """Create database tables."""
        self.logger.info("Creating database tables")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            
            # Enable SQLite extensions and optimizations
            if "sqlite" in str(self.engine.url):
                await self._setup_sqlite_extensions(conn)
                
        self.logger.info("Database tables created successfully")
    
    async def _setup_sqlite_extensions(self, conn) -> None:
        """Setup SQLite-specific extensions and optimizations."""
        statements = [
            # Enable WAL mode for better concurrency
            "PRAGMA journal_mode=WAL;" if settings.database.wal_mode else "",
            
            # Performance optimizations
            "PRAGMA synchronous=NORMAL;",
            "PRAGMA cache_size=10000;",
            "PRAGMA temp_store=MEMORY;",
            "PRAGMA mmap_size=268435456;",  # 256MB
            
            # Create FTS5 table for full-text search
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
                title, content, source_path, doc_metadata,
                content_rowid UNINDEXED
            );
            """ if settings.database.fts_enabled else "",
            
            # Create FTS5 trigger to keep it in sync
            """
            CREATE TRIGGER IF NOT EXISTS document_fts_insert AFTER INSERT ON document BEGIN
                INSERT INTO document_fts(rowid, title, content, source_path, doc_metadata, content_rowid)
                VALUES (new.rowid, new.title, new.content, new.source_path, new.doc_metadata, new.id);
            END;
            """ if settings.database.fts_enabled else "",
            
            """
            CREATE TRIGGER IF NOT EXISTS document_fts_update AFTER UPDATE ON document BEGIN
                UPDATE document_fts SET 
                    title=new.title, 
                    content=new.content, 
                    source_path=new.source_path,
                    doc_metadata=new.doc_metadata
                WHERE rowid=old.rowid;
            END;
            """ if settings.database.fts_enabled else "",
            
            """
            CREATE TRIGGER IF NOT EXISTS document_fts_delete AFTER DELETE ON document BEGIN
                DELETE FROM document_fts WHERE rowid=old.rowid;
            END;
            """ if settings.database.fts_enabled else "",
        ]
        
        for stmt in statements:
            if stmt.strip():
                await conn.execute(text(stmt))
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager."""
        async with self.async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # Document operations
    async def create_document(self, document: Document) -> Document:
        """Create a new document."""
        async with self.get_session() as session:
            session.add(document)
            await session.commit()
            await session.refresh(document)
            
            self.logger.info(
                "Document created",
                document_id=document.id,
                title=document.title,
                source_type=document.source_type
            )
            
            return document
    
    async def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID."""
        async with self.get_session() as session:
            return await session.get(Document, document_id)
    
    async def get_document_by_hash(self, content_hash: str) -> Optional[Document]:
        """Get document by content hash."""
        async with self.get_session() as session:
            statement = select(Document).where(Document.content_hash == content_hash)
            result = await session.execute(statement)
            return result.scalar_one_or_none()
    
    async def update_document_embedding(self, document_id: int, embedding: np.ndarray) -> None:
        """Update document embedding vector."""
        async with self.get_session() as session:
            document = await session.get(Document, document_id)
            if document:
                # Serialize numpy array to bytes
                document.embedding_vector = embedding.tobytes()
                await session.commit()
                
                self.logger.debug(
                    "Document embedding updated",
                    document_id=document_id,
                    vector_shape=embedding.shape
                )
    
    async def get_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        source_type: Optional[str] = None
    ) -> List[Document]:
        """Get paginated list of documents."""
        async with self.get_session() as session:
            statement = select(Document)
            
            if source_type:
                statement = statement.where(Document.source_type == source_type)
                
            statement = statement.offset(offset).limit(limit).order_by(Document.created_at.desc())
            
            result = await session.execute(statement)
            return result.scalars().all()
    
    # Entity operations
    async def create_entity(self, entity: Entity) -> Entity:
        """Create a new entity."""
        async with self.get_session() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            
            self.logger.info(
                "Entity created",
                entity_id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type
            )
            
            return entity
    
    async def get_or_create_entity(self, name: str, entity_type: str) -> Entity:
        """Get existing entity or create new one."""
        async with self.get_session() as session:
            statement = select(Entity).where(
                Entity.name == name,
                Entity.entity_type == entity_type
            )
            result = await session.execute(statement)
            entity = result.scalar_one_or_none()
            
            if not entity:
                entity = Entity(name=name, entity_type=entity_type, confidence=1.0)
                session.add(entity)
                await session.commit()
                await session.refresh(entity)
                
                self.logger.info(
                    "New entity created",
                    entity_id=entity.id,
                    name=name,
                    entity_type=entity_type
                )
            
            return entity
    
    async def link_document_entity(
        self,
        document_id: int,
        entity_id: int,
        mentions: int = 1,
        positions: Optional[List[int]] = None,
        confidence: float = 1.0
    ) -> DocumentEntity:
        """Create document-entity relationship."""
        async with self.get_session() as session:
            doc_entity = DocumentEntity(
                document_id=document_id,
                entity_id=entity_id,
                mentions=mentions,
                positions=json.dumps(positions) if positions else None,
                confidence=confidence
            )
            
            session.add(doc_entity)
            await session.commit()
            await session.refresh(doc_entity)
            
            return doc_entity
    
    # Relationship operations
    async def create_relationship(self, relationship: Relationship) -> Relationship:
        """Create entity relationship."""
        async with self.get_session() as session:
            session.add(relationship)
            await session.commit()
            await session.refresh(relationship)
            
            self.logger.info(
                "Relationship created",
                relationship_id=relationship.id,
                source_entity_id=relationship.source_entity_id,
                target_entity_id=relationship.target_entity_id,
                relation_type=relationship.relation_type
            )
            
            return relationship
    
    # Search operations
    async def fulltext_search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Tuple[Document, float]]:
        """Perform full-text search using FTS5."""
        if not settings.database.fts_enabled:
            return []
        
        async with self.get_session() as session:
            # FTS5 search with ranking
            fts_query = """
            SELECT 
                document.*, 
                document_fts.rank
            FROM document_fts
            JOIN document ON document.id = document_fts.content_rowid
            WHERE document_fts MATCH ?
            ORDER BY document_fts.rank
            LIMIT ? OFFSET ?
            """
            
            result = await session.execute(
                text(fts_query),
                (query, limit, offset)
            )
            
            documents_with_scores = []
            for row in result:
                doc = Document(**{col: getattr(row, col) for col in Document.__table__.columns.keys()})
                score = row.rank
                documents_with_scores.append((doc, score))
            
            return documents_with_scores
    
    async def vector_search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[Document, float]]:
        """Perform vector similarity search."""
        async with self.get_session() as session:
            # Get documents with embeddings
            statement = select(Document).where(Document.embedding_vector.is_not(None))
            result = await session.execute(statement)
            documents = result.scalars().all()
            
            # Calculate similarities
            similarities = []
            query_norm = np.linalg.norm(query_vector)
            
            for doc in documents:
                if doc.embedding_vector:
                    # Deserialize numpy array from bytes
                    doc_vector = np.frombuffer(doc.embedding_vector, dtype=np.float32)
                    
                    # Reshape if needed (assuming we stored flattened vectors)
                    if doc_vector.size == query_vector.size:
                        doc_vector = doc_vector.reshape(query_vector.shape)
                        
                        # Cosine similarity
                        doc_norm = np.linalg.norm(doc_vector)
                        if doc_norm > 0 and query_norm > 0:
                            similarity = np.dot(query_vector, doc_vector) / (query_norm * doc_norm)
                            
                            if similarity >= threshold:
                                similarities.append((doc, float(similarity)))
            
            # Sort by similarity descending and limit results
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]
    
    # Chat operations
    async def save_chat_message(self, message: ChatMessage) -> ChatMessage:
        """Save chat message."""
        async with self.get_session() as session:
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            return message
    
    async def get_chat_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get chat message history for session."""
        async with self.get_session() as session:
            statement = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            
            result = await session.execute(statement)
            messages = result.scalars().all()
            return list(reversed(messages))  # Return in chronological order
    
    # Analytics operations
    async def log_search_query(self, query: SearchQuery) -> SearchQuery:
        """Log search query for analytics."""
        async with self.get_session() as session:
            session.add(query)
            await session.commit()
            await session.refresh(query)
            
            return query
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        async with self.get_session() as session:
            # Count documents
            doc_count = await session.execute(text("SELECT COUNT(*) FROM document"))
            doc_total = doc_count.scalar()
            
            # Count entities
            entity_count = await session.execute(text("SELECT COUNT(*) FROM entity"))
            entity_total = entity_count.scalar()
            
            # Count relationships
            rel_count = await session.execute(text("SELECT COUNT(*) FROM relationship"))
            rel_total = rel_count.scalar()
            
            # Count chat messages
            chat_count = await session.execute(text("SELECT COUNT(*) FROM chatmessage"))
            chat_total = chat_count.scalar()
            
            return {
                "documents": doc_total,
                "entities": entity_total,
                "relationships": rel_total,
                "chat_messages": chat_total,
                "database_path": settings.database.path,
                "fts_enabled": settings.database.fts_enabled,
            }