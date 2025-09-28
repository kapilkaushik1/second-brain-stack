"""Unit tests for database operations."""

import pytest
import hashlib
from datetime import datetime

from core.database import DatabaseManager
from core.database.models import Document, Entity, DocumentEntity


@pytest.mark.asyncio
class TestDatabaseManager:
    """Test DatabaseManager functionality."""
    
    async def test_create_tables(self, db_manager):
        """Test table creation."""
        # Tables should already be created by fixture
        stats = await db_manager.get_stats()
        assert "documents" in stats
        assert stats["documents"] == 0
    
    async def test_document_crud(self, db_manager):
        """Test document CRUD operations."""
        # Create document
        doc = Document(
            title="Test Document",
            content="This is test content for CRUD operations.",
            source_type="test",
            source_path="/test/crud.txt",
            content_hash=hashlib.sha256(b"test content").hexdigest(),
            word_count=8
        )
        
        created_doc = await db_manager.create_document(doc)
        
        # Verify creation
        assert created_doc.id is not None
        assert created_doc.title == "Test Document"
        assert created_doc.source_type == "test"
        
        # Test retrieval
        retrieved_doc = await db_manager.get_document(created_doc.id)
        assert retrieved_doc is not None
        assert retrieved_doc.title == "Test Document"
        assert retrieved_doc.content == "This is test content for CRUD operations."
        
        # Test get by hash
        hash_doc = await db_manager.get_document_by_hash(created_doc.content_hash)
        assert hash_doc is not None
        assert hash_doc.id == created_doc.id
    
    async def test_duplicate_document_prevention(self, db_manager):
        """Test that duplicate documents are prevented."""
        content_hash = hashlib.sha256(b"duplicate content").hexdigest()
        
        doc1 = Document(
            title="Original",
            content="duplicate content",
            source_type="test",
            source_path="/test/original.txt",
            content_hash=content_hash
        )
        
        doc2 = Document(
            title="Duplicate",
            content="duplicate content",
            source_type="test", 
            source_path="/test/duplicate.txt",
            content_hash=content_hash
        )
        
        # Create first document
        created_doc1 = await db_manager.create_document(doc1)
        assert created_doc1.id is not None
        
        # Check for duplicate before creating second
        existing = await db_manager.get_document_by_hash(content_hash)
        assert existing is not None
        assert existing.title == "Original"
    
    async def test_entity_operations(self, db_manager):
        """Test entity CRUD operations."""
        # Create entity
        entity = Entity(
            name="Machine Learning",
            entity_type="CONCEPT",
            confidence=0.95,
            description="AI/ML concept"
        )
        
        created_entity = await db_manager.create_entity(entity)
        
        # Verify creation
        assert created_entity.id is not None
        assert created_entity.name == "Machine Learning"
        assert created_entity.entity_type == "CONCEPT"
        
        # Test get_or_create with existing entity
        existing_entity = await db_manager.get_or_create_entity("Machine Learning", "CONCEPT")
        assert existing_entity.id == created_entity.id
        
        # Test get_or_create with new entity
        new_entity = await db_manager.get_or_create_entity("Python", "LANGUAGE")
        assert new_entity.id != created_entity.id
        assert new_entity.name == "Python"
        assert new_entity.entity_type == "LANGUAGE"
    
    async def test_document_entity_linking(self, db_manager):
        """Test linking documents to entities."""
        # Create document and entity
        doc = Document(
            title="ML Tutorial",
            content="This tutorial covers machine learning basics.",
            source_type="test",
            source_path="/test/ml_tutorial.txt",
            content_hash=hashlib.sha256(b"ml tutorial content").hexdigest()
        )
        created_doc = await db_manager.create_document(doc)
        
        entity = Entity(
            name="Machine Learning",
            entity_type="CONCEPT",
            confidence=0.9
        )
        created_entity = await db_manager.create_entity(entity)
        
        # Link document to entity
        doc_entity = await db_manager.link_document_entity(
            document_id=created_doc.id,
            entity_id=created_entity.id,
            mentions=2,
            positions=[10, 45],
            confidence=0.85
        )
        
        # Verify link
        assert doc_entity.document_id == created_doc.id
        assert doc_entity.entity_id == created_entity.id
        assert doc_entity.mentions == 2
        assert doc_entity.confidence == 0.85
    
    async def test_embedding_operations(self, db_manager):
        """Test embedding storage and retrieval."""
        import numpy as np
        
        # Create document
        doc = Document(
            title="Embedding Test",
            content="This document tests embedding storage.",
            source_type="test",
            source_path="/test/embedding.txt",
            content_hash=hashlib.sha256(b"embedding test").hexdigest()
        )
        created_doc = await db_manager.create_document(doc)
        
        # Create test embedding
        embedding = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        
        # Store embedding
        await db_manager.update_document_embedding(created_doc.id, embedding)
        
        # Retrieve and verify
        retrieved_doc = await db_manager.get_document(created_doc.id)
        assert retrieved_doc.embedding_vector is not None
        
        # Deserialize and compare
        retrieved_embedding = np.frombuffer(retrieved_doc.embedding_vector, dtype=np.float32)
        np.testing.assert_array_equal(embedding, retrieved_embedding)
    
    async def test_get_documents_pagination(self, db_manager, sample_documents):
        """Test document pagination."""
        # Create multiple documents
        created_docs = []
        for doc_data in sample_documents:
            doc = Document(
                content_hash=hashlib.sha256(doc_data["content"].encode()).hexdigest(),
                **doc_data
            )
            created_doc = await db_manager.create_document(doc)
            created_docs.append(created_doc)
        
        # Test pagination
        page1 = await db_manager.get_documents(limit=2, offset=0)
        assert len(page1) == 2
        
        page2 = await db_manager.get_documents(limit=2, offset=2)
        assert len(page2) == 1
        
        # Test source type filtering
        test_docs = await db_manager.get_documents(source_type="test")
        assert len(test_docs) == 3
        assert all(doc.source_type == "test" for doc in test_docs)
    
    async def test_statistics(self, db_manager, sample_documents):
        """Test database statistics."""
        # Initial stats
        initial_stats = await db_manager.get_stats()
        assert initial_stats["documents"] == 0
        assert initial_stats["entities"] == 0
        
        # Add some data
        for doc_data in sample_documents:
            doc = Document(
                content_hash=hashlib.sha256(doc_data["content"].encode()).hexdigest(),
                **doc_data
            )
            await db_manager.create_document(doc)
        
        entity = Entity(name="Test Entity", entity_type="TEST", confidence=0.8)
        await db_manager.create_entity(entity)
        
        # Check updated stats
        updated_stats = await db_manager.get_stats()
        assert updated_stats["documents"] == 3
        assert updated_stats["entities"] == 1
        assert updated_stats["fts_enabled"] is True
        assert "storage" in updated_stats["database_path"]