"""SQLModel database models for the second brain stack."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class DocumentBase(SQLModel):
    """Base document model."""
    
    title: str = Field(index=True, description="Document title")
    content: str = Field(description="Full document content")
    source_type: str = Field(index=True, description="Source type (filesystem, web, git, etc.)")
    source_path: str = Field(index=True, description="Original source path or URL")
    content_hash: str = Field(unique=True, index=True, description="SHA-256 hash of content")
    doc_metadata: Optional[str] = Field(default=None, description="JSON metadata")
    
    # Content analysis
    word_count: Optional[int] = Field(default=None, description="Number of words")
    language: Optional[str] = Field(default="en", description="Detected language")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    indexed_at: Optional[datetime] = Field(default=None, description="Last indexing timestamp")


class Document(DocumentBase, table=True):
    """Document table model."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Vector embedding (stored as bytes - serialized numpy array)
    embedding_vector: Optional[bytes] = Field(default=None, description="Serialized embedding vector")
    
    # Relationships
    entities: List["DocumentEntity"] = Relationship(back_populates="document")


class EntityBase(SQLModel):
    """Base entity model."""
    
    name: str = Field(unique=True, index=True, description="Entity name")
    entity_type: str = Field(index=True, description="Entity type (PERSON, ORG, etc.)")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    description: Optional[str] = Field(default=None, description="Entity description")
    
    # Metadata
    aliases: Optional[str] = Field(default=None, description="JSON array of aliases")
    external_ids: Optional[str] = Field(default=None, description="JSON object of external IDs")
    
    # Statistics
    mention_count: int = Field(default=1, description="Number of mentions across documents")
    
    # Timestamps
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="First seen timestamp")
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last seen timestamp")


class Entity(EntityBase, table=True):
    """Entity table model."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    documents: List["DocumentEntity"] = Relationship(back_populates="entity")
    source_relationships: List["Relationship"] = Relationship(
        back_populates="source_entity",
        sa_relationship_kwargs={"foreign_keys": "Relationship.source_entity_id"}
    )
    target_relationships: List["Relationship"] = Relationship(
        back_populates="target_entity", 
        sa_relationship_kwargs={"foreign_keys": "Relationship.target_entity_id"}
    )


class DocumentEntityBase(SQLModel):
    """Base document-entity relationship model."""
    
    document_id: int = Field(foreign_key="document.id", primary_key=True)
    entity_id: int = Field(foreign_key="entity.id", primary_key=True)
    
    # Context information
    mentions: int = Field(default=1, description="Number of mentions in this document")
    positions: Optional[str] = Field(default=None, description="JSON array of character positions")
    context_snippets: Optional[str] = Field(default=None, description="JSON array of context snippets")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this relationship")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentEntity(DocumentEntityBase, table=True):
    """Document-Entity association table."""
    
    document: Document = Relationship(back_populates="entities")
    entity: Entity = Relationship(back_populates="documents")


class RelationshipBase(SQLModel):
    """Base relationship model."""
    
    source_entity_id: int = Field(foreign_key="entity.id")
    target_entity_id: int = Field(foreign_key="entity.id")
    relation_type: str = Field(index=True, description="Type of relationship")
    
    # Evidence and confidence
    confidence: float = Field(ge=0.0, le=1.0, description="Relationship confidence score")
    evidence_count: int = Field(default=1, description="Number of supporting documents")
    
    # Context
    description: Optional[str] = Field(default=None, description="Human-readable description")
    rel_metadata: Optional[str] = Field(default=None, description="JSON metadata")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))


class Relationship(RelationshipBase, table=True):
    """Relationship table model."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    source_entity: Entity = Relationship(
        back_populates="source_relationships",
        sa_relationship_kwargs={"foreign_keys": "Relationship.source_entity_id"}
    )
    target_entity: Entity = Relationship(
        back_populates="target_relationships",
        sa_relationship_kwargs={"foreign_keys": "Relationship.target_entity_id"}
    )


class SearchQueryBase(SQLModel):
    """Base search query model."""
    
    query_text: str = Field(description="Original search query")
    query_type: str = Field(description="Type of search (fulltext, semantic, hybrid)")
    
    # Results metadata
    total_results: int = Field(default=0, description="Total number of results")
    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    
    # User context
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchQuery(SearchQueryBase, table=True):
    """Search query log table."""
    
    id: Optional[int] = Field(default=None, primary_key=True)


class ChatMessageBase(SQLModel):
    """Base chat message model."""
    
    session_id: str = Field(index=True, description="Chat session identifier")
    message_type: str = Field(description="Message type (user, assistant, system)")
    content: str = Field(description="Message content")
    
    # Context and metadata
    context_documents: Optional[str] = Field(default=None, description="JSON array of document IDs used for context")
    msg_metadata: Optional[str] = Field(default=None, description="JSON metadata")
    
    # Processing info
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    model_used: Optional[str] = Field(default=None, description="Model used for generation")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(ChatMessageBase, table=True):
    """Chat message table."""
    
    id: Optional[int] = Field(default=None, primary_key=True)