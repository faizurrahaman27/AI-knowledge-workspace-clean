"""
Autonomous Learning System Models

Database models for Knowledge Graph, Notebooks, Learning Paths, Insights, and Memory.
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
    """Knowledge graph entity types."""
    PERSON = "person"
    COMPANY = "company"
    TECHNOLOGY = "technology"
    LIBRARY = "library"
    COUNTRY = "country"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    SKILL = "skill"
    ALGORITHM = "algorithm"
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATE = "date"
    EVENT = "event"
    CONCEPT = "concept"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Knowledge graph relationship types."""
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    IMPLEMENTS = "implements"
    USES = "uses"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    REFERENCES = "references"
    DEFINES = "defines"
    EXTENDS = "extends"
    PRECEDES = "precedes"
    LEADS_TO = "leads_to"


class QuestionDifficulty(str, Enum):
    """Question difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class QuestionType(str, Enum):
    """Question types."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    CODING = "coding"
    SCENARIO_BASED = "scenario_based"
    REASONING = "reasoning"


class FlashcardType(str, Enum):
    """Flashcard types."""
    DEFINITION = "definition"
    CONCEPT = "concept"
    CODE = "code"
    FORMULA = "formula"
    LANGUAGE = "language"


class JobStatus(str, Enum):
    """Background job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Knowledge Graph - Nodes
# ============================================================================

class KnowledgeNode(Base):
    """
    Knowledge graph node representing an entity.
    """
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    node_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)
    
    # User & Document
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Properties
    description = Column(Text, nullable=True)
    aliases = Column(JSON, nullable=True)
    language = Column(String(10), default="en")
    
    # Metadata
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_chunk_id = Column(Integer, nullable=True)
    citation = Column(Text, nullable=True)
    
    # Scoring
    confidence_score = Column(Float, default=0.0)
    importance_score = Column(Float, default=0.5)
    
    # Embedding
    embedding_vector = Column(JSON, nullable=True)
    
    # Counts
    in_degree = Column(Integer, default=0)
    out_degree = Column(Integer, default=0)
    
    # Timestamps
    first_seen_at = Column(DateTime, nullable=True)
    last_updated_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    document = relationship("Document")
    outgoing_relationships = relationship("KnowledgeEdge", foreign_keys="KnowledgeEdge.source_node_id", back_populates="source_node")
    incoming_relationships = relationship("KnowledgeEdge", foreign_keys="KnowledgeEdge.target_node_id", back_populates="target_node")

    __table_args__ = (
        Index('ix_knowledge_nodes_user', 'user_id'),
        Index('ix_knowledge_nodes_type', 'entity_type'),
        Index('ix_knowledge_nodes_name', 'name'),
    )


# ============================================================================
# Knowledge Graph - Edges
# ============================================================================

class KnowledgeEdge(Base):
    """
    Knowledge graph edge representing a relationship.
    """
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, index=True)
    
    # Edge identity
    edge_id = Column(String(100), unique=True, nullable=False)
    
    # Connection
    source_node_id = Column(Integer, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    
    # Properties
    description = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)
    
    # Source
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    citation = Column(Text, nullable=True)
    
    # Scoring
    confidence_score = Column(Float, default=0.0)
    
    # Metadata
    is_auto_generated = Column(Boolean, default=True)
    is_validated = Column(Boolean, default=False)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    source_node = relationship("KnowledgeNode", foreign_keys=[source_node_id], back_populates="outgoing_relationships")
    target_node = relationship("KnowledgeNode", foreign_keys=[target_node_id], back_populates="incoming_relationships")
    document = relationship("Document")

    __table_args__ = (
        Index('ix_knowledge_edges_source', 'source_node_id'),
        Index('ix_knowledge_edges_target', 'target_node_id'),
        Index('ix_knowledge_edges_type', 'relationship_type'),
    )


# ============================================================================
# Intelligent Notebooks
# ============================================================================

class IntelligentNotebook(Base):
    """
    Intelligent notebook that organizes knowledge.
    """
    __tablename__ = "intelligent_notebooks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    notebook_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Knowledge content
    document_ids = Column(JSON, nullable=True)
    concept_ids = Column(JSON, nullable=True)
    entity_ids = Column(JSON, nullable=True)
    
    # Auto-generated content
    auto_summary = Column(Text, nullable=True)
    auto_timeline = Column(JSON, nullable=True)
    auto_concept_map = Column(JSON, nullable=True)
    auto_quotations = Column(JSON, nullable=True)
    auto_mind_map = Column(JSON, nullable=True)
    
    # Statistics
    document_count = Column(Integer, default=0)
    concept_count = Column(Integer, default=0)
    entity_count = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    flashcard_count = Column(Integer, default=0)
    
    # Knowledge metrics
    knowledge_confidence = Column(Float, default=0.0)
    coverage_score = Column(Float, default=0.0)
    
    # Settings
    is_public = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('ix_notebooks_user', 'user_id'),
    )


# ============================================================================
# Learning Paths
# ============================================================================

class LearningPath(Base):
    """
    Learning path for a topic.
    """
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    path_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Topic
    topic = Column(String(200), nullable=False)
    
    # Structure
    prerequisites = Column(JSON, nullable=True)
    steps = Column(JSON, nullable=True)  # [{step, title, description, document_ids, estimated_time}]
    dependencies = Column(JSON, nullable=True)
    
    # Metrics
    total_estimated_hours = Column(Float, default=0.0)
    difficulty_level = Column(String(20), default="intermediate")
    completion_percentage = Column(Float, default=0.0)
    
    # Recommendations
    recommended_documents = Column(JSON, nullable=True)
    recommended_videos = Column(JSON, nullable=True)
    recommended_repositories = Column(JSON, nullable=True)
    recommended_books = Column(JSON, nullable=True)
    recommended_papers = Column(JSON, nullable=True)
    
    # Progress
    completed_steps = Column(JSON, nullable=True)
    current_step = Column(Integer, default=0)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('ix_learning_paths_user', 'user_id'),
        Index('ix_learning_paths_topic', 'topic'),
    )


# ============================================================================
# Knowledge Insights
# ============================================================================

class KnowledgeInsight(Base):
    """
    Generated knowledge insights.
    """
    __tablename__ = "knowledge_insights"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    insight_id = Column(String(100), unique=True, nullable=False)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Insight content
    insight_type = Column(String(50), nullable=False)  # important_topics, connected_concepts, gaps, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Related entities
    related_node_ids = Column(JSON, nullable=True)
    related_document_ids = Column(JSON, nullable=True)
    
    # Scoring
    importance_score = Column(Float, default=0.5)
    confidence_score = Column(Float, default=0.5)
    
    # Generation
    generated_by = Column(String(50), nullable=True)
    generation_method = Column(String(50), nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('ix_insights_user', 'user_id'),
        Index('ix_insights_type', 'insight_type'),
    )


# ============================================================================
# AI Memory
# ============================================================================

class AIMemory(Base):
    """
    Long-term AI memory for the workspace.
    """
    __tablename__ = "ai_memory"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    memory_id = Column(String(100), unique=True, nullable=False)
    
    # User & Workspace
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    
    # Memory type
    memory_type = Column(String(50), nullable=False)  # conversation, workspace, research, discovery
    
    # Content
    key = Column(String(200), nullable=False)
    value = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Tags for retrieval
    tags = Column(JSON, nullable=True)
    
    # Importance
    importance_score = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # TTL
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    workspace = relationship("Workspace")

    __table_args__ = (
        Index('ix_ai_memory_user', 'user_id'),
        Index('ix_ai_memory_type', 'memory_type'),
        Index('ix_ai_memory_key', 'key'),
    )


# ============================================================================
# Background Jobs
# ============================================================================

class BackgroundJob(Base):
    """
    Background job for autonomous processing.
    """
    __tablename__ = "background_jobs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    job_id = Column(String(100), unique=True, nullable=False)
    job_type = Column(String(50), nullable=False)  # extract, summarize, embed, etc.
    job_name = Column(String(200), nullable=False)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Target
    target_type = Column(String(50), nullable=True)  # document, notebook, etc.
    target_id = Column(String(100), nullable=True)
    
    # Job data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default=JobStatus.PENDING.value)
    progress = Column(Float, default=0.0)
    current_step = Column(String(100), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timing
    priority = Column(Integer, default=5)
    estimated_duration_seconds = Column(Integer, nullable=True)
    actual_duration_seconds = Column(Integer, nullable=True)
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('ix_background_jobs_user', 'user_id'),
        Index('ix_background_jobs_status', 'status'),
        Index('ix_background_jobs_type', 'job_type'),
    )


# ============================================================================
# Document Evolution
# ============================================================================

class DocumentVersion(Base):
    """
    Document version history for knowledge evolution.
    """
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Document
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Version info
    version = Column(Integer, nullable=False)
    change_type = Column(String(50), nullable=False)  # summary_evolution, entity_evolution, etc.
    
    # Snapshot
    snapshot_data = Column(JSON, nullable=True)  # Snapshot of entities, topics, etc.
    previous_snapshot = Column(JSON, nullable=True)
    
    # Diff
    changes = Column(JSON, nullable=True)  # Added, removed, modified
    diff_summary = Column(Text, nullable=True)
    
    # Metrics
    entity_count_before = Column(Integer, default=0)
    entity_count_after = Column(Integer, default=0)
    concept_count_before = Column(Integer, default=0)
    concept_count_after = Column(Integer, default=0)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_doc_versions_document', 'document_id'),
    )


# ============================================================================
# Learning Progress
# ============================================================================

class LearningProgress(Base):
    """
    Track user's learning progress.
    """
    __tablename__ = "learning_progress"

    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Topic
    topic = Column(String(200), nullable=False)
    
    # Progress
    comprehension_level = Column(Float, default=0.0)  # 0-1
    practice_count = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    
    # Spaced repetition
    next_review_at = Column(DateTime, nullable=True)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    
    # Mastery
    is_mastered = Column(Boolean, default=False)
    mastered_at = Column(DateTime, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    last_practiced_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('ix_learning_progress_user', 'user_id'),
        Index('ix_learning_progress_topic', 'topic'),
        UniqueConstraint('user_id', 'topic', name='uq_user_topic_progress'),
    )
