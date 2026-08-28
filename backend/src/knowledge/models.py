"""
Knowledge Models

Database models for storing structured knowledge extracted from documents.
Each model is designed for specific knowledge types with proper relationships.
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


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    ORGANIZATION = "organization"
    COMPANY = "company"
    TECHNOLOGY = "technology"
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    MODEL = "model"
    DATASET = "dataset"
    LIBRARY = "library"
    EQUATION = "equation"
    TOOL = "tool"
    WEBSITE = "website"
    RESEARCH_PAPER = "research_paper"
    BOOK = "book"
    INSTITUTION = "institution"
    PRODUCT = "product"
    EVENT = "event"
    LOCATION = "location"
    DATE = "date"
    NUMBER = "number"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Types of relationships between concepts/entities."""
    USES = "uses"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    REQUIRES = "requires"
    ENABLES = "enables"
    EXTENDS = "extends"
    COMPOSED_OF = "composed_of"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    DEFINED_IN = "defined_in"
    INTRODUCED_BY = "introduced_by"
    AUTHORED_BY = "authored_by"
    PUBLISHED_IN = "published_in"
    LOCATED_IN = "located_in"
    OCCURS_IN = "occurs_in"


class QuestionType(str, Enum):
    """Types of questions that can be generated."""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    CONCEPTUAL = "conceptual"
    ANALYTICAL = "analytical"
    SCENARIO_BASED = "scenario_based"
    CODING = "coding"


class DifficultyLevel(str, Enum):
    """Difficulty levels for questions and flashcards."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TagCategory(str, Enum):
    """Categories for semantic tags."""
    SKILL = "skill"
    TECHNOLOGY = "technology"
    INDUSTRY = "industry"
    ACADEMIC_DOMAIN = "academic_domain"
    PROGRAMMING_LANGUAGE = "programming_language"
    LIBRARY = "library"
    FRAMEWORK = "framework"
    RESEARCH_AREA = "research_area"
    CAREER_DOMAIN = "career_domain"


# ============================================================================
# Document Summary
# ============================================================================

class DocumentSummary(Base):
    """
    Stores multiple levels of summary for a document.
    Each document can have one summary per level.
    """
    __tablename__ = "document_summaries"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Summary levels
    one_sentence_summary = Column(Text, nullable=True)  # One sentence overview
    executive_summary = Column(Text, nullable=True)      # Brief executive overview
    bullet_summary = Column(Text, nullable=True)         # Bullet points
    detailed_summary = Column(Text, nullable=True)      # Full detailed summary
    chapter_summary = Column(JSON, nullable=True)        # {chapter_title: summary}
    
    # Metadata
    version = Column(Integer, default=1)
    confidence_score = Column(Float, nullable=True)     # 0.0 to 1.0
    processing_time_ms = Column(Integer, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="summary")

    __table_args__ = (
        Index('ix_summaries_document', 'document_id'),
        UniqueConstraint('document_id', name='uq_summary_document'),
    )


# ============================================================================
# Knowledge Entity
# ============================================================================

class KnowledgeEntity(Base):
    """
    Extracted entities from documents.
    Stores canonical entity information to avoid duplicates.
    """
    __tablename__ = "knowledge_entities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Entity information
    name = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)  # EntityType enum
    canonical_name = Column(String(500), nullable=True)  # Standardized name
    description = Column(Text, nullable=True)
    
    # Context
    mentions = Column(Integer, default=1)              # Number of mentions
    first_mention = Column(Text, nullable=True)       # First occurrence context
    aliases = Column(JSON, nullable=True)             # Alternative names
    
    # Location
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(500), nullable=True)
    
    # Quality
    confidence_score = Column(Float, nullable=True)   # 0.0 to 1.0
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="entities")

    __table_args__ = (
        Index('ix_entities_document', 'document_id'),
        Index('ix_entities_type', 'entity_type'),
        Index('ix_entities_name', 'name'),
    )


# ============================================================================
# Knowledge Concept
# ============================================================================

class KnowledgeConcept(Base):
    """
    Extracted concepts independent of entities.
    Represents abstract ideas, techniques, methods, etc.
    """
    __tablename__ = "knowledge_concepts"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Concept information
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification
    importance = Column(String(20), nullable=True)    # high, medium, low
    difficulty = Column(String(20), nullable=True)   # DifficultyLevel
    
    # Relationships
    related_concepts = Column(JSON, nullable=True)    # List of related concept names
    related_entities = Column(JSON, nullable=True)   # List of entity IDs
    
    # Context
    first_definition = Column(Text, nullable=True)
    usage_examples = Column(JSON, nullable=True)      # List of usage contexts
    
    # Quality
    confidence_score = Column(Float, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="concepts")

    __table_args__ = (
        Index('ix_concepts_document', 'document_id'),
        Index('ix_concepts_name', 'name'),
    )


# ============================================================================
# Knowledge Relationship
# ============================================================================

class KnowledgeRelationship(Base):
    """
    Extracted relationships between entities and concepts.
    Forms the basis for knowledge graph generation.
    """
    __tablename__ = "knowledge_relationships"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Source and target
    source_type = Column(String(20), nullable=False)  # 'entity' or 'concept'
    source_id = Column(Integer, nullable=False)
    source_name = Column(String(500), nullable=False)
    
    # Relationship
    relationship_type = Column(String(50), nullable=False)  # RelationshipType
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=False)
    target_name = Column(String(500), nullable=False)
    
    # Context
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)            # Text evidence for relationship
    page_number = Column(Integer, nullable=True)
    
    # Quality
    confidence_score = Column(Float, nullable=True)
    is_inferred = Column(Boolean, default=False)      # True if inferred, False if explicit
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="relationships")

    __table_args__ = (
        Index('ix_relationships_document', 'document_id'),
        Index('ix_relationships_source', 'source_type', 'source_id'),
        Index('ix_relationships_target', 'target_type', 'target_id'),
        Index('ix_relationships_type', 'relationship_type'),
    )


# ============================================================================
# Generated Question
# ============================================================================

class GeneratedQuestion(Base):
    """
    Auto-generated questions for learning and assessment.
    """
    __tablename__ = "generated_questions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Question content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # QuestionType
    difficulty = Column(String(20), nullable=False)     # DifficultyLevel
    
    # Answer (for short answer) or options (for MCQ)
    answer = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)              # List of options for MCQ
    correct_option_index = Column(Integer, nullable=True)
    
    # Context
    topic = Column(String(500), nullable=True)        # Related topic
    related_concept = Column(String(500), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    
    # Quality
    confidence_score = Column(Float, nullable=True)
    
    # Usage
    usage_count = Column(Integer, default=0)          # Times used in quiz
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="questions")

    __table_args__ = (
        Index('ix_questions_document', 'document_id'),
        Index('ix_questions_type', 'question_type'),
        Index('ix_questions_difficulty', 'difficulty'),
    )


# ============================================================================
# Knowledge Flashcard
# ============================================================================

class KnowledgeFlashcard(Base):
    """
    Auto-generated flashcards for spaced repetition learning.
    """
    __tablename__ = "knowledge_flashcards"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    front = Column(Text, nullable=False)              # Question/prompt
    back = Column(Text, nullable=False)                # Answer
    
    # Classification
    topic = Column(String(500), nullable=True)
    tags = Column(JSON, nullable=True)                # Related tags
    difficulty = Column(String(20), nullable=False)   # DifficultyLevel
    
    # Source reference
    source_reference = Column(Text, nullable=True)     # Page/section reference
    related_concept = Column(String(500), nullable=True)
    
    # Quality
    confidence_score = Column(Float, nullable=True)
    
    # Spaced repetition (Anki-style)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime, nullable=True)
    last_reviewed = Column(DateTime, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="flashcards")

    __table_args__ = (
        Index('ix_flashcards_document', 'document_id'),
        Index('ix_flashcards_topic', 'topic'),
        Index('ix_flashcards_next_review', 'next_review'),
    )


# ============================================================================
# Document Topic
# ============================================================================

class DocumentTopic(Base):
    """
    Classified topics for a document.
    """
    __tablename__ = "document_topics"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Topic information
    topic_name = Column(String(500), nullable=False)
    topic_type = Column(String(50), nullable=True)     # primary, secondary, tertiary
    
    # Hierarchy
    category = Column(String(100), nullable=True)     # Broad category
    subcategory = Column(String(100), nullable=True)  # Sub-category
    hierarchy_path = Column(JSON, nullable=True)       # Full hierarchy path
    
    # Relationships
    prerequisite_topics = Column(JSON, nullable=True) # Topics needed first
    related_topics = Column(JSON, nullable=True)      # Related topic names
    
    # Quality
    confidence_score = Column(Float, nullable=True)
    importance_score = Column(Float, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="topics")

    __table_args__ = (
        Index('ix_topics_document', 'document_id'),
        Index('ix_topics_name', 'topic_name'),
        Index('ix_topics_category', 'category'),
    )


# ============================================================================
# Semantic Tag
# ============================================================================

class SemanticTag(Base):
    """
    Semantic tags for classification and discovery.
    """
    __tablename__ = "semantic_tags"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Tag information
    tag = Column(String(200), nullable=False)
    tag_category = Column(String(50), nullable=False)  # TagCategory
    
    # Context
    context = Column(Text, nullable=True)              # How tag was derived
    relevance_score = Column(Float, nullable=True)    # 0.0 to 1.0
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="semantic_tags")

    __table_args__ = (
        Index('ix_tags_document', 'document_id'),
        Index('ix_tags_category', 'tag_category'),
        Index('ix_tags_tag', 'tag'),
        UniqueConstraint('document_id', 'tag', 'tag_category', name='uq_tag_document_category'),
    )


# ============================================================================
# Document Section
# ============================================================================

class DocumentSection(Base):
    """
    Detected logical sections within a document.
    """
    __tablename__ = "document_sections"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Section information
    title = Column(String(500), nullable=True)
    level = Column(Integer, default=1)                 # Heading level (1, 2, 3...)
    
    # Position
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    
    # Content summary
    summary = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True)         # List of key points
    
    # Metadata
    estimated_reading_time_minutes = Column(Float, nullable=True)
    
    # Order
    order_index = Column(Integer, nullable=False)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="sections")

    __table_args__ = (
        Index('ix_sections_document', 'document_id'),
        Index('ix_sections_order', 'document_id', 'order_index'),
    )


# ============================================================================
# Knowledge Metadata
# ============================================================================

class KnowledgeMetadata(Base):
    """
    Overall knowledge extraction metadata for a document.
    """
    __tablename__ = "knowledge_metadata"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Document metadata
    language = Column(String(10), nullable=True)       # ISO language code
    language_name = Column(String(50), nullable=True)
    
    # Classification
    document_category = Column(String(100), nullable=True)
    academic_subject = Column(String(200), nullable=True)
    industry_tags = Column(JSON, nullable=True)        # Industry classifications
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)       # Overall extraction quality
    completeness_score = Column(Float, nullable=True) # How complete the extraction is
    
    # Time estimates
    reading_time_minutes = Column(Float, nullable=True)
    difficulty_score = Column(Float, nullable=True)   # 0.0 to 1.0 (easy to hard)
    
    # Processing info
    processing_version = Column(String(50), nullable=True)
    models_used = Column(JSON, nullable=True)          # Which models were used
    processing_duration_ms = Column(Integer, nullable=True)
    
    # Counts
    entity_count = Column(Integer, default=0)
    concept_count = Column(Integer, default=0)
    relationship_count = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    flashcard_count = Column(Integer, default=0)
    section_count = Column(Integer, default=0)
    
    # Status
    extraction_complete = Column(Boolean, default=False)
    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="knowledge_metadata")

    __table_args__ = (
        Index('ix_metadata_document', 'document_id'),
        UniqueConstraint('document_id', name='uq_metadata_document'),
    )


# ============================================================================
# Update Document model to include relationships
# ============================================================================

# Note: These will be added to the existing Document model via relationship definitions
# The following properties need to be added to Document model:
# - summary: relationship("DocumentSummary", back_populates="document", uselist=False)
# - entities: relationship("KnowledgeEntity", back_populates="document")
# - concepts: relationship("KnowledgeConcept", back_populates="document")
# - relationships: relationship("KnowledgeRelationship", back_populates="document")
# - questions: relationship("GeneratedQuestion", back_populates="document")
# - flashcards: relationship("KnowledgeFlashcard", back_populates="document")
# - topics: relationship("DocumentTopic", back_populates="document")
# - semantic_tags: relationship("SemanticTag", back_populates="document")
# - sections: relationship("DocumentSection", back_populates="document")
# - knowledge_metadata: relationship("KnowledgeMetadata", back_populates="document", uselist=False)
