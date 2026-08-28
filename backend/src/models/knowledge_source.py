"""
Knowledge Source Model

Unified model for all knowledge sources (documents, websites, GitHub files,
videos, research papers, datasets, etc.) with common metadata structure.

This model extends the existing Document model to provide a unified
interface for all knowledge source types while maintaining backward
compatibility with the existing Document model.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Float, Boolean
from sqlalchemy.orm import relationship

from src.db.database import Base


class SourceType(Enum):
    """
    Enumeration of all supported knowledge source types.
    
    Each type represents a different ingestion pathway with specific
    processing requirements and metadata fields.
    """
    # Document sources
    PDF = "pdf"
    DOCUMENT = "document"  # Generic document (Word, etc.)
    
    # Web sources
    WEB_PAGE = "web_page"
    WEB_ARTICLE = "web_article"
    WEB_DOCUMENTATION = "web_documentation"
    
    # Code sources
    GITHUB_FILE = "github_file"
    GITHUB_REPO = "github_repo"  # Future: full repo indexing
    CODE_SNIPPET = "code_snippet"
    
    # Media sources
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"  # With OCR
    
    # Academic sources
    RESEARCH_PAPER = "research_paper"
    ARXIV_PAPER = "arxiv_paper"
    
    # Data sources
    DATASET = "dataset"
    SPREADSHEET = "spreadsheet"
    
    # Other
    SCAN = "scan"  # OCR-processed scan
    EMAIL = "email"
    NOTE = "note"  # User-created notes


class ProcessingStatus(Enum):
    """Status of knowledge source processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some content failed to process


class KnowledgeSource(Base):
    """
    Unified model for all knowledge sources.
    
    This model provides a common metadata structure for all types of
    knowledge sources, enabling consistent querying and processing
    across different source types.
    
    Design Principles:
    1. Backward compatible with existing Document model
    2. Extensible for new source types
    3. Complete metadata for processing decisions
    4. Relationship to workspaces for organization
    
    Usage:
        source = KnowledgeSource(
            source_type=SourceType.PDF,
            name="My Document.pdf",
            workspace_id=workspace.id,
            owner_id=user.id,
            metadata={...}
        )
    """
    
    __tablename__ = "knowledge_sources"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # === Core Identification ===
    name = Column(String, nullable=False)  # Display name
    source_type = Column(String, nullable=False)  # SourceType enum value
    
    # === Relationships ===
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    
    # === Source Location ===
    # Local file path (for uploaded files)
    file_path = Column(String, nullable=True)
    
    # External URL (for web, GitHub, etc.)
    source_url = Column(String, nullable=True)
    
    # Content type
    content_type = Column(String, nullable=True)
    
    # Size info
    size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)  # For documents
    duration_seconds = Column(Integer, nullable=True)  # For media
    
    # === Processing Status ===
    processing_status = Column(String, nullable=False, default=ProcessingStatus.PENDING.value)
    processing_error = Column(Text, nullable=True)
    
    # Language detection
    language_code = Column(String, nullable=True)
    language_name = Column(String, nullable=True)
    
    # === Metadata (JSON for extensibility) ===
    # Source-specific metadata stored as JSON
    # Examples:
    # - PDF: {"author": "...", "title": "...", "creation_date": "..."}
    # - GitHub: {"repo": "...", "owner": "...", "branch": "...", "path": "..."}
    # - Video: {"duration": 3600, "transcript": "...", "thumbnail_url": "..."}
    # - Research: {"authors": [...], "abstract": "...", "doi": "...", "venue": "..."}
    source_metadata = Column(JSON, nullable=True, default=dict)
    
    # Tags for organization and discovery
    tags = Column(JSON, nullable=True, default=list)
    
    # Categories for grouping
    categories = Column(JSON, nullable=True, default=list)
    
    # === Quality & Relevance ===
    # Auto-computed quality score (0-1)
    quality_score = Column(Float, nullable=True)
    
    # User-rated relevance (0-5 stars)
    user_rating = Column(Integer, nullable=True)
    
    # Verified by user (for research papers, etc.)
    verified = Column(Boolean, default=False)
    
    # === Timestamps ===
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
    last_accessed_at = Column(DateTime, nullable=True)
    last_processed_at = Column(DateTime, nullable=True)
    
    # === Relationships ===
    owner = relationship("User", back_populates=None)
    workspace = relationship("Workspace", back_populates=None)
    
    # Relationship to original Document for backward compatibility
    # One KnowledgeSource can be linked to one legacy Document
    legacy_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    # === Indexes ===
    # Index for common queries
    __table_args__ = (
        # Index for workspace queries
        Index('ix_knowledge_sources_workspace', 'workspace_id'),
        # Index for owner queries
        Index('ix_knowledge_sources_owner', 'owner_id'),
        # Index for type queries
        Index('ix_knowledge_sources_type', 'source_type'),
        # Index for status queries
        Index('ix_knowledge_sources_status', 'processing_status'),
    )
    
    @property
    def is_processed(self) -> bool:
        """Check if the source has been fully processed."""
        return self.processing_status == ProcessingStatus.INDEXED.value
    
    @property
    def is_processing(self) -> bool:
        """Check if the source is currently being processed."""
        return self.processing_status == ProcessingStatus.PROCESSING.value
    
    @property
    def display_type(self) -> str:
        """Get human-readable type name."""
        type_names = {
            SourceType.PDF.value: "PDF Document",
            SourceType.WEB_PAGE.value: "Web Page",
            SourceType.WEB_ARTICLE.value: "Web Article",
            SourceType.WEB_DOCUMENTATION.value: "Documentation",
            SourceType.GITHUB_FILE.value: "GitHub File",
            SourceType.GITHUB_REPO.value: "GitHub Repository",
            SourceType.VIDEO.value: "Video",
            SourceType.AUDIO.value: "Audio",
            SourceType.RESEARCH_PAPER.value: "Research Paper",
            SourceType.DATASET.value: "Dataset",
            SourceType.SCAN.value: "Scanned Document",
            SourceType.NOTE.value: "Note",
        }
        return type_names.get(self.source_type, self.source_type)
    
    @property
    def icon(self) -> str:
        """Get icon identifier for UI display."""
        icons = {
            SourceType.PDF.value: "file-text",
            SourceType.WEB_PAGE.value: "globe",
            SourceType.WEB_ARTICLE.value: "newspaper",
            SourceType.WEB_DOCUMENTATION.value: "book-open",
            SourceType.GITHUB_FILE.value: "code",
            SourceType.GITHUB_REPO.value: "folder-code",
            SourceType.VIDEO.value: "video",
            SourceType.AUDIO.value: "headphones",
            SourceType.RESEARCH_PAPER.value: "graduation-cap",
            SourceType.DATASET.value: "database",
            SourceType.SCAN.value: "camera",
            SourceType.NOTE.value: "edit",
        }
        return icons.get(self.source_type, "file")
    
    def get_summary(self) -> dict:
        """Get a summary dict for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type,
            "display_type": self.display_type,
            "icon": self.icon,
            "processing_status": self.processing_status,
            "language": self.language_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "source_url": self.source_url,
            "tags": self.tags or [],
            "categories": self.categories or [],
            "quality_score": self.quality_score,
            "verified": self.verified,
        }
    
    def update_last_accessed(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def __repr__(self) -> str:
        return f"<KnowledgeSource(id={self.id}, name='{self.name}', type={self.source_type})>"


# Add missing import for Index
from sqlalchemy import Index
