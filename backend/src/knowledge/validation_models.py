"""
Knowledge Validation Models

Database models for knowledge validation, quality assurance, and audit trail.
These models ensure traceability, reliability, and trustworthiness of extracted knowledge.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, 
    Boolean, JSON, Float, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from src.db.database import Base


class ValidationStatus(str, Enum):
    """Validation status values."""
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationType(str, Enum):
    """Types of validation checks."""
    CITATION = "citation"
    CONSISTENCY = "consistency"
    DUPLICATE = "duplicate"
    ENTITY_RESOLUTION = "entity_resolution"
    REFERENCE_INTEGRITY = "reference_integrity"
    SEMANTIC = "semantic"
    FORMAT = "format"
    PROVENANCE = "provenance"


class AuditEventType(str, Enum):
    """Types of audit events."""
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    ENTITY_MERGED = "entity_merged"
    DUPLICATE_REMOVED = "duplicate_removed"
    CITATION_CREATED = "citation_created"
    QUALITY_SCORE_CALCULATED = "quality_score_calculated"
    CONFIDENCE_CALCULATED = "confidence_calculated"
    VERSION_UPDATED = "version_updated"
    VALIDATION_WARNING = "validation_warning"
    VALIDATION_ERROR = "validation_error"


class SourceType(str, Enum):
    """Types of source references."""
    DOCUMENT = "document"
    PAGE = "page"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    CHUNK = "chunk"
    SENTENCE = "sentence"


# ============================================================================
# Knowledge Citation
# ============================================================================

class KnowledgeCitation(Base):
    """
    Tracks the source of each piece of extracted knowledge.
    Enables traceability from generated content back to original documents.
    """
    __tablename__ = "knowledge_citations"

    id = Column(Integer, primary_key=True, index=True)
    
    # What was cited
    knowledge_type = Column(String(50), nullable=False)  # entity, concept, relationship, etc.
    knowledge_id = Column(Integer, nullable=False)
    
    # Source reference
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(20), nullable=False)  # page, section, paragraph, chunk
    source_id = Column(String(100), nullable=True)    # ID within source
    
    # Location in source
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(500), nullable=True)
    paragraph_index = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    sentence_index = Column(Integer, nullable=True)
    
    # Text excerpt from source
    text_excerpt = Column(Text, nullable=True)
    character_start = Column(Integer, nullable=True)
    character_end = Column(Integer, nullable=True)
    
    # Citation quality
    relevance_score = Column(Float, nullable=True)  # How relevant this citation is
    is_primary = Column(Boolean, default=False)      # Primary citation vs supporting
    
    # Provenance chain
    provenance_chain = Column(JSON, nullable=True)  # [{type, id, description}]
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_citations_knowledge', 'knowledge_type', 'knowledge_id'),
        Index('ix_citations_document', 'document_id'),
    )


# ============================================================================
# Validation Record
# ============================================================================

class ValidationRecord(Base):
    """
    Records the result of each validation check.
    Provides detailed validation history for debugging and auditing.
    """
    __tablename__ = "validation_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Context
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # What was validated
    validation_type = Column(String(50), nullable=False)  # ValidationType
    knowledge_type = Column(String(50), nullable=True)      # entity, concept, etc.
    knowledge_id = Column(Integer, nullable=True)          # ID of validated item
    
    # Validation result
    status = Column(String(20), nullable=False)            # ValidationStatus
    passed = Column(Boolean, nullable=False)
    
    # Details
    message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)                # Additional details
    
    # Remediation
    remediation_action = Column(String(100), nullable=True)
    remediation_applied = Column(Boolean, default=False)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_validation_document', 'document_id'),
        Index('ix_validation_type', 'validation_type'),
        Index('ix_validation_status', 'status'),
    )


# ============================================================================
# Canonical Entity
# ============================================================================

class CanonicalEntity(Base):
    """
    Canonical (normalized) representation of entities.
    Enables cross-document entity recognition and deduplication.
    """
    __tablename__ = "canonical_entities"

    id = Column(Integer, primary_key=True, index=True)
    
    # Canonical name (normalized)
    canonical_name = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)
    
    # Aliases (variations of the same entity)
    aliases = Column(JSON, nullable=True, default=list)  # ["OpenAI", "Open AI", "Open-AI"]
    
    # Merged entities
    merged_entity_ids = Column(JSON, nullable=True)     # IDs of merged entities
    
    # Statistics
    occurrence_count = Column(Integer, default=0)       # Total mentions
    document_count = Column(Integer, default=0)          # Documents containing this entity
    
    # Description
    canonical_description = Column(Text, nullable=True)
    
    # First and last seen
    first_seen = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    __table_args__ = (
        Index('ix_canonical_name', 'canonical_name'),
        Index('ix_canonical_type', 'entity_type'),
        UniqueConstraint('canonical_name', 'entity_type', name='uq_canonical_name_type'),
    )


# ============================================================================
# Knowledge Version
# ============================================================================

class KnowledgeVersion(Base):
    """
    Tracks version history of knowledge extractions.
    Enables reprocessing and rollback.
    """
    __tablename__ = "knowledge_versions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Context
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Version info
    version_number = Column(Integer, nullable=False)
    is_current = Column(Boolean, default=True)
    
    # Processing details
    extraction_version = Column(String(50), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    llm_provider = Column(String(100), nullable=True)
    llm_model = Column(String(100), nullable=True)
    embedding_model = Column(String(100), nullable=True)
    
    # Processing info
    processing_strategy = Column(String(100), nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    
    # Quality metrics for this version
    quality_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Timestamps
    extraction_timestamp = Column(DateTime, nullable=True)
    validation_timestamp = Column(DateTime, nullable=True)
    
    # Changelog
    changelog = Column(Text, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_version_document', 'document_id'),
        Index('ix_version_current', 'document_id', 'is_current'),
    )


# ============================================================================
# Knowledge Audit
# ============================================================================

class KnowledgeAudit(Base):
    """
    Audit log for all knowledge processing operations.
    Provides complete traceability of all changes.
    """
    __tablename__ = "knowledge_audit"

    id = Column(Integer, primary_key=True, index=True)
    
    # Context
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    
    # Event details
    event_type = Column(String(50), nullable=False)       # AuditEventType
    knowledge_type = Column(String(50), nullable=True)      # entity, concept, etc.
    knowledge_id = Column(Integer, nullable=True)          # ID of affected item
    
    # Description
    description = Column(Text, nullable=False)
    
    # Actor
    actor_type = Column(String(20), nullable=True)        # system, user, api
    actor_id = Column(String(100), nullable=True)
    
    # Change details
    action = Column(String(50), nullable=False)          # create, update, delete, merge
    previous_value = Column(JSON, nullable=True)           # Value before change
    new_value = Column(JSON, nullable=True)              # Value after change
    
    # Processing context
    service_name = Column(String(100), nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    
    # Metadata
    validation_metadata = Column(JSON, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_audit_document', 'document_id'),
        Index('ix_audit_event_type', 'event_type'),
        Index('ix_audit_created', 'created_at'),
        Index('ix_audit_knowledge', 'knowledge_type', 'knowledge_id'),
    )


# ============================================================================
# Knowledge Quality
# ============================================================================

class KnowledgeQuality(Base):
    """
    Overall quality metrics for document knowledge.
    Provides a single score for knowledge quality ranking.
    """
    __tablename__ = "knowledge_quality"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Overall scores
    overall_quality_score = Column(Float, nullable=True)      # 0.0 to 1.0
    overall_confidence_score = Column(Float, nullable=True)    # 0.0 to 1.0
    
    # Component scores
    extraction_completeness = Column(Float, nullable=True)    # How complete is extraction
    entity_quality = Column(Float, nullable=True)            # Entity extraction quality
    relationship_quality = Column(Float, nullable=True)       # Relationship quality
    summary_quality = Column(Float, nullable=True)           # Summary quality
    citation_coverage = Column(Float, nullable=True)          # % of knowledge with citations
    topic_coverage = Column(Float, nullable=True)            # Topic coverage score
    metadata_completeness = Column(Float, nullable=True)     # Metadata completeness
    knowledge_density = Column(Float, nullable=True)         # Knowledge per document length
    
    # Counts
    total_entities = Column(Integer, default=0)
    total_concepts = Column(Integer, default=0)
    total_relationships = Column(Integer, default=0)
    total_citations = Column(Integer, default=0)
    validated_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    
    # Validation stats
    validation_passed = Column(Integer, default=0)
    validation_warnings = Column(Integer, default=0)
    validation_errors = Column(Integer, default=0)
    
    # Timestamps
    calculated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    
    # Version
    version_id = Column(Integer, ForeignKey("knowledge_versions.id"), nullable=True)

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_quality_document', 'document_id'),
        Index('ix_quality_score', 'overall_quality_score'),
    )


# ============================================================================
# Update existing models with validation references
# ============================================================================

# Note: The following fields should be added to existing models:
#
# KnowledgeEntity:
#   - canonical_entity_id: FK to CanonicalEntity
#   - validation_status: ValidationStatus
#
# KnowledgeConcept:
#   - validation_status: ValidationStatus
#
# KnowledgeRelationship:
#   - validation_status: ValidationStatus
#
# DocumentSummary:
#   - validation_status: ValidationStatus
#
# GeneratedQuestion:
#   - validation_status: ValidationStatus
#
# KnowledgeFlashcard:
#   - validation_status: ValidationStatus
