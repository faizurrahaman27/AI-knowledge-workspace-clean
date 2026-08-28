"""
Research Operating System Models

Database models for research projects, evidence, reports, and research workflow.
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


class ResearchStatus(str, Enum):
    """Research status values."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class EvidenceSource(str, Enum):
    """Evidence source types."""
    WORKSPACE = "workspace"
    WEB_PAGE = "web_page"
    DOCUMENTATION = "documentation"
    GITHUB = "github"
    ARXIV = "arxiv"
    DOI = "doi"
    BLOG = "blog"
    VIDEO = "video"
    USER_UPLOAD = "user_upload"


class ValidationConfidence(str, Enum):
    """Source validation confidence levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


# ============================================================================
# Research Project
# ============================================================================

class ResearchProject(Base):
    """
    Research project for organizing research goals and findings.
    """
    __tablename__ = "research_projects"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Scope
    scope = Column(Text, nullable=True)  # Research scope/boundaries
    keywords = Column(JSON, nullable=True)  # Research keywords
    tags = Column(JSON, nullable=True)  # User tags
    
    # Status
    status = Column(String(20), default=ResearchStatus.PLANNING.value)
    
    # Progress
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    # Confidence
    overall_confidence = Column(Float, nullable=True)
    evidence_count = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
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
    tasks = relationship("ResearchTask", back_populates="project", cascade="all, delete-orphan")
    evidence = relationship("ResearchEvidence", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("ResearchReport", back_populates="project", cascade="all, delete-orphan")
    sessions = relationship("ResearchSession", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_projects_user', 'user_id'),
        Index('ix_projects_status', 'status'),
    )


# ============================================================================
# Research Task
# ============================================================================

class ResearchTask(Base):
    """
    Individual research task within a project.
    """
    __tablename__ = "research_tasks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    
    # Task details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Type
    task_type = Column(String(50), nullable=True)  # gather, analyze, compare, synthesize
    
    # Status
    status = Column(String(20), default=TaskStatus.PENDING.value)
    priority = Column(Integer, default=5)  # 1-10, 1 being highest
    
    # Hierarchy
    parent_task_id = Column(Integer, ForeignKey("research_tasks.id", ondelete="CASCADE"), nullable=True)
    
    # Execution
    assigned_agent = Column(String(100), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    
    # Results
    findings = Column(JSON, nullable=True)  # Task findings
    blockers = Column(Text, nullable=True)  # What blocked this task
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
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
    project = relationship("ResearchProject", back_populates="tasks")
    parent_task = relationship("ResearchTask", remote_side=[id], backref="subtasks")
    evidence = relationship("ResearchEvidence", back_populates="task")

    __table_args__ = (
        Index('ix_tasks_project', 'project_id'),
        Index('ix_tasks_status', 'status'),
        Index('ix_tasks_parent', 'parent_task_id'),
    )


# ============================================================================
# Evidence
# ============================================================================

class ResearchEvidence(Base):
    """
    Evidence collected during research.
    """
    __tablename__ = "research_evidence"

    id = Column(Integer, primary_key=True, index=True)
    
    # Project & Task
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("research_tasks.id", ondelete="SET NULL"), nullable=True)
    
    # Evidence content
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Full content or excerpt
    
    # Source
    source_type = Column(String(50), nullable=False)  # EvidenceSource
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(500), nullable=True)  # e.g., "OpenAI Documentation"
    author = Column(String(500), nullable=True)
    publication = Column(String(500), nullable=True)
    published_date = Column(DateTime, nullable=True)
    
    # Citation
    citation_key = Column(String(100), nullable=True)  # e.g., "[Smith2024]"
    
    # Validation
    authority_score = Column(Float, nullable=True)  # 0.0-1.0
    freshness_score = Column(Float, nullable=True)  # 0.0-1.0
    popularity_score = Column(Float, nullable=True)  # 0.0-1.0
    workspace_trust = Column(Boolean, default=False)  # From user's workspace
    validation_confidence = Column(String(20), default=ValidationConfidence.UNKNOWN.value)
    
    # Ranking
    relevance_score = Column(Float, default=0.0)  # 0.0-1.0
    credibility_score = Column(Float, default=0.0)  # 0.0-1.0
    overall_score = Column(Float, default=0.0)  # Combined ranking score
    
    # Knowledge integration
    linked_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    citations = Column(JSON, nullable=True)  # Knowledge citations
    
    # Status
    is_validated = Column(Boolean, default=False)
    is_pertinent = Column(Boolean, default=True)  # Relevant to research
    
    # Timestamps
    retrieval_timestamp = Column(DateTime, nullable=True)
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
    project = relationship("ResearchProject", back_populates="evidence")
    task = relationship("ResearchTask", back_populates="evidence")
    document = relationship("Document")

    __table_args__ = (
        Index('ix_evidence_project', 'project_id'),
        Index('ix_evidence_task', 'task_id'),
        Index('ix_evidence_source', 'source_type'),
        Index('ix_evidence_score', 'overall_score'),
    )


# ============================================================================
# Conflict
# ============================================================================

class ResearchConflict(Base):
    """
    Detected conflicts between evidence.
    """
    __tablename__ = "research_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    
    # Conflict details
    conflict_type = Column(String(50), nullable=False)  # claim, definition, date, metric, conclusion
    description = Column(Text, nullable=False)
    
    # Conflicting evidence
    evidence_a_id = Column(Integer, ForeignKey("research_evidence.id", ondelete="SET NULL"), nullable=True)
    evidence_b_id = Column(Integer, ForeignKey("research_evidence.id", ondelete="SET NULL"), nullable=True)
    
    # Resolution
    resolution_status = Column(String(20), default="unresolved")  # unresolved, resolved, acknowledged
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
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
    evidence_a = relationship("ResearchEvidence", foreign_keys=[evidence_a_id])
    evidence_b = relationship("ResearchEvidence", foreign_keys=[evidence_b_id])

    __table_args__ = (
        Index('ix_conflicts_project', 'project_id'),
        Index('ix_conflicts_type', 'conflict_type'),
    )


# ============================================================================
# Research Report
# ============================================================================

class ResearchReport(Base):
    """
    Generated research report.
    """
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    
    # Report metadata
    title = Column(String(500), nullable=False)
    report_type = Column(String(50), default="comprehensive")  # comprehensive, executive, technical
    version = Column(Integer, default=1)
    
    # Content sections (stored as JSON for flexibility)
    executive_summary = Column(Text, nullable=True)
    technical_summary = Column(Text, nullable=True)
    beginner_explanation = Column(Text, nullable=True)
    comparison_table = Column(JSON, nullable=True)
    pros_cons = Column(JSON, nullable=True)  # {pros: [], cons: []}
    consensus = Column(Text, nullable=True)
    disagreements = Column(Text, nullable=True)
    open_questions = Column(JSON, nullable=True)  # [{question, related_evidence}]
    future_research = Column(Text, nullable=True)
    
    # Analysis
    evidence_used = Column(JSON, nullable=True)  # List of evidence IDs
    conflicts_addressed = Column(JSON, nullable=True)  # List of conflict IDs
    key_findings = Column(JSON, nullable=True)  # List of key findings
    
    # Confidence
    research_confidence = Column(Float, nullable=True)
    methodology_notes = Column(Text, nullable=True)
    
    # References
    references = Column(JSON, nullable=True)  # Formatted citations
    
    # Notebook integration
    notebook_note_id = Column(Integer, ForeignKey("knowledge_notes.id", ondelete="SET NULL"), nullable=True)
    collection_id = Column(Integer, ForeignKey("knowledge_collections.id", ondelete="SET NULL"), nullable=True)
    
    # Export
    export_formats = Column(JSON, nullable=True)  # ["markdown", "html"]
    
    # Timestamps
    generated_at = Column(DateTime, nullable=True)
    updated_at = Column(
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
    project = relationship("ResearchProject", back_populates="reports")

    __table_args__ = (
        Index('ix_reports_project', 'project_id'),
        Index('ix_reports_type', 'report_type'),
    )


# ============================================================================
# Research Session
# ============================================================================

class ResearchSession(Base):
    """
    Research session for tracking research workflow.
    """
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    
    # Session info
    session_type = Column(String(50), nullable=False)  # planning, gathering, analysis, synthesis
    goal = Column(Text, nullable=True)
    
    # Execution
    queries_executed = Column(JSON, nullable=True)  # List of queries
    evidence_collected = Column(Integer, default=0)
    tasks_executed = Column(Integer, default=0)
    
    # Agent actions
    agent_actions = Column(JSON, nullable=True)  # [{action, timestamp, result}]
    
    # Results
    session_summary = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="in_progress")
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    project = relationship("ResearchProject", back_populates="sessions")

    __table_args__ = (
        Index('ix_sessions_project', 'project_id'),
        Index('ix_sessions_type', 'session_type'),
    )


# ============================================================================
# Research Plan
# ============================================================================

class ResearchPlan(Base):
    """
    Generated research plan.
    """
    __tablename__ = "research_plans"

    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    
    # Plan content
    research_goal = Column(Text, nullable=False)
    objectives = Column(JSON, nullable=True)  # List of objectives
    research_questions = Column(JSON, nullable=True)  # List of research questions
    subtasks = Column(JSON, nullable=True)  # Decomposed subtasks
    expected_sources = Column(JSON, nullable=True)  # Expected source types
    missing_information = Column(JSON, nullable=True)  # Gaps identified
    
    # Complexity
    estimated_complexity = Column(String(20), nullable=True)  # low, medium, high
    estimated_duration_hours = Column(Float, nullable=True)
    
    # Priority
    priority_order = Column(JSON, nullable=True)  # Ordered list of tasks
    
    # Execution
    execution_plan = Column(JSON, nullable=True)  # Step-by-step plan
    is_approved = Column(Boolean, default=False)
    
    # Version
    version = Column(Integer, default=1)
    
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

    __table_args__ = (
        Index('ix_plans_project', 'project_id'),
    )
