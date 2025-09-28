"""Unit tests for database models."""

import pytest
from datetime import datetime

from core.database.models import Document, Entity, Relationship, DocumentEntity, ChatMessage


class TestDocument:
    """Test Document model."""
    
    def test_document_creation(self):
        """Test creating a document."""
        doc = Document(
            title="Test Document",
            content="This is test content",
            source_type="test",
            source_path="/test/path",
            content_hash="abc123",
            word_count=4
        )
        
        assert doc.title == "Test Document"
        assert doc.content == "This is test content"
        assert doc.source_type == "test"
        assert doc.source_path == "/test/path"
        assert doc.content_hash == "abc123"
        assert doc.word_count == 4
        assert doc.language == "en"
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)
    
    def test_document_with_metadata(self):
        """Test document with metadata."""
        metadata = '{"file_size": 1024, "mime_type": "text/plain"}'
        
        doc = Document(
            title="Test Doc",
            content="Content",
            source_type="filesystem",
            source_path="/test/file.txt",
            content_hash="xyz789",
            doc_metadata=metadata
        )
        
        assert doc.doc_metadata == metadata
    
    def test_document_defaults(self):
        """Test document default values."""
        doc = Document(
            title="Test",
            content="Content",
            source_type="test",
            source_path="/test",
            content_hash="hash123"
        )
        
        assert doc.language == "en"
        assert doc.word_count is None
        assert doc.doc_metadata is None
        assert doc.indexed_at is None


class TestEntity:
    """Test Entity model."""
    
    def test_entity_creation(self):
        """Test creating an entity."""
        entity = Entity(
            name="Python",
            entity_type="LANGUAGE",
            confidence=0.95,
            description="Programming language"
        )
        
        assert entity.name == "Python"
        assert entity.entity_type == "LANGUAGE"
        assert entity.confidence == 0.95
        assert entity.description == "Programming language"
        assert entity.mention_count == 1
        assert isinstance(entity.first_seen, datetime)
        assert isinstance(entity.last_seen, datetime)
    
    def test_entity_validation(self):
        """Test entity validation."""
        # Test confidence bounds - Pydantic validation
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Entity(
                name="Test",
                entity_type="TEST",
                confidence=1.5  # Should be <= 1.0
            )
        
        with pytest.raises(ValidationError):
            Entity(
                name="Test", 
                entity_type="TEST",
                confidence=-0.1  # Should be >= 0.0
            )


class TestRelationship:
    """Test Relationship model."""
    
    def test_relationship_creation(self):
        """Test creating a relationship."""
        rel = Relationship(
            source_entity_id=1,
            target_entity_id=2,
            relation_type="RELATED_TO",
            confidence=0.8,
            evidence_count=3,
            description="Test relationship"
        )
        
        assert rel.source_entity_id == 1
        assert rel.target_entity_id == 2
        assert rel.relation_type == "RELATED_TO"
        assert rel.confidence == 0.8
        assert rel.evidence_count == 3
        assert rel.description == "Test relationship"
        assert isinstance(rel.created_at, datetime)
        assert isinstance(rel.updated_at, datetime)


class TestDocumentEntity:
    """Test DocumentEntity association model."""
    
    def test_document_entity_creation(self):
        """Test creating document-entity association."""
        doc_entity = DocumentEntity(
            document_id=1,
            entity_id=2,
            mentions=3,
            confidence=0.9,
            positions='[10, 25, 50]'
        )
        
        assert doc_entity.document_id == 1
        assert doc_entity.entity_id == 2
        assert doc_entity.mentions == 3
        assert doc_entity.confidence == 0.9
        assert doc_entity.positions == '[10, 25, 50]'
        assert isinstance(doc_entity.created_at, datetime)


class TestChatMessage:
    """Test ChatMessage model."""
    
    def test_chat_message_creation(self):
        """Test creating a chat message."""
        message = ChatMessage(
            session_id="session123",
            message_type="user",
            content="Hello, how are you?",
            processing_time_ms=150.5,
            model_used="gpt-3.5-turbo"
        )
        
        assert message.session_id == "session123"
        assert message.message_type == "user"
        assert message.content == "Hello, how are you?"
        assert message.processing_time_ms == 150.5
        assert message.model_used == "gpt-3.5-turbo"
        assert isinstance(message.created_at, datetime)