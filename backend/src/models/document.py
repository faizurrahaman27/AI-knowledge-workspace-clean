"""
Document Model

Represents an uploaded or imported knowledge source.
Each document can have associated knowledge intelligence (extracted entities, concepts, etc.).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from src.db.database import Base


class Document(Base):
    """
    Document model representing an uploaded or imported knowledge source.
    
    Documents are processed through the knowledge intelligence pipeline
    to extract structured knowledge including entities, concepts, relationships,
    summaries, questions, and flashcards.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String, nullable=False)

    file_path = Column(String, nullable=False)

    content_type = Column(String, nullable=True)

    size_bytes = Column(Integer, nullable=True)

    # ISO 639-1 code (e.g. "en", "hi") and a human-readable name, detected
    # from the extracted text at ingestion time. Powers the dual-language
    # answer feature.
    language_code = Column(String, nullable=True)

    language_name = Column(String, nullable=True)

    # For non-upload sources (website, GitHub file) -- where this came
    # from, shown in the UI so a user can tell "PDF I uploaded" apart
    # from "page I imported." Null for direct PDF/scan uploads.
    source_url = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    owner_id = Column(Integer, ForeignKey("users.id"))

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)

    # Knowledge extraction status
    knowledge_extracted = Column(Integer, default=0)  # 0 = not started, 1 = in progress, 2 = complete
    extraction_error = Column(String, nullable=True)

    owner = relationship(
        "User",
        back_populates="documents",
    )

    workspace = relationship("Workspace", back_populates="documents")
    
    # === Knowledge Intelligence Relationships ===
    
    # Summary (one-to-one)
    summary = relationship(
        "DocumentSummary",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Entities (one-to-many)
    entities = relationship(
        "KnowledgeEntity",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Concepts (one-to-many)
    concepts = relationship(
        "KnowledgeConcept",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Relationships (one-to-many)
    relationships = relationship(
        "KnowledgeRelationship",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Questions (one-to-many)
    questions = relationship(
        "GeneratedQuestion",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Flashcards (one-to-many)
    flashcards = relationship(
        "KnowledgeFlashcard",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Topics (one-to-many)
    topics = relationship(
        "DocumentTopic",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Semantic Tags (one-to-many)
    semantic_tags = relationship(
        "SemanticTag",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Sections (one-to-many)
    sections = relationship(
        "DocumentSection",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    # Knowledge Metadata (one-to-one)
    knowledge_metadata = relationship(
        "KnowledgeMetadata",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"
    )
