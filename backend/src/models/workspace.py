"""
Workspace Model

Enhanced workspace model with comprehensive metadata, organization features,
and relationship management for the AI Knowledge Workspace.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import relationship

from src.db.database import Base


class WorkspaceStatus(str, Enum):
    """Workspace lifecycle states."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Workspace(Base):
    """
    Workspace model for organizing knowledge sources.
    
    A workspace is a container for related knowledge sources, chat history,
    and metadata. Workspaces can be personal (owned by a user) or 
    collaborative (owned by a team).
    
    Features:
    - Name and description
    - Tags for organization
    - Archive/restore functionality
    - Favorite marking
    - Source count and statistics
    - Processing status tracking
    """
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # A workspace belongs to EITHER a personal owner OR a team, not both.
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # Organization
    tags = Column(JSON, nullable=True, default=list)  # ["machine-learning", "nlp", "research"]
    status = Column(String(50), nullable=False, default=WorkspaceStatus.ACTIVE.value)
    
    # User preferences
    is_favorite = Column(Boolean, default=False)
    color = Column(String(7), nullable=True)  # Hex color for UI, e.g., "#3B82F6"
    icon = Column(String(50), nullable=True)  # Emoji or icon identifier
    
    # Statistics (updated periodically)
    source_count = Column(Integer, default=0)
    chat_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    
    # Processing status
    processing_status = Column(String(50), nullable=True)  # "idle", "processing", "error"
    last_processed_at = Column(DateTime, nullable=True)
    
    # Timestamps
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
    archived_at = Column(DateTime, nullable=True)
    
    # Metadata (extensible JSON for future use)
    settings_metadata = Column(JSON)
    
    # Relationships
    owner = relationship("User", back_populates="workspaces")
    team = relationship("Team", back_populates="workspaces")
    documents = relationship("Document", back_populates="workspace")
    chats = relationship("Chat", back_populates="workspace")
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_workspaces_owner_status', 'owner_id', 'status'),
        Index('ix_workspaces_team_status', 'team_id', 'status'),
        Index('ix_workspaces_favorite', 'owner_id', 'is_favorite'),
    )
    
    @property
    def is_archived(self) -> bool:
        """Check if workspace is archived."""
        return self.status == WorkspaceStatus.ARCHIVED.value
    
    @property
    def is_deleted(self) -> bool:
        """Check if workspace is deleted."""
        return self.status == WorkspaceStatus.DELETED.value
    
    @property
    def is_active(self) -> bool:
        """Check if workspace is active."""
        return self.status == WorkspaceStatus.ACTIVE.value
    
    def archive(self) -> None:
        """Mark workspace as archived."""
        self.status = WorkspaceStatus.ARCHIVED.value
        self.archived_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def restore(self) -> None:
        """Restore workspace from archive."""
        self.status = WorkspaceStatus.ACTIVE.value
        self.archived_at = None
    
    def toggle_favorite(self) -> bool:
        """Toggle favorite status, return new value."""
        self.is_favorite = not self.is_favorite
        return self.is_favorite
    
    def update_last_accessed(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def update_statistics(self, source_count: int, chat_count: int, total_size: int) -> None:
        """Update workspace statistics."""
        self.source_count = source_count
        self.chat_count = chat_count
        self.total_size_bytes = total_size
        self.last_processed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to workspace."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from workspace."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def to_summary(self) -> dict:
        """Get workspace summary for list views."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "is_favorite": self.is_favorite,
            "color": self.color,
            "icon": self.icon,
            "source_count": self.source_count,
            "chat_count": self.chat_count,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
        }
    
    def to_detail(self) -> dict:
        """Get workspace details with full information."""
        return {
            **self.to_summary(),
            "owner_id": self.owner_id,
            "team_id": self.team_id,
            "total_size_bytes": self.total_size_bytes,
            "processing_status": self.processing_status,
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "metadata": self.settings_metadata or {},
        }
    
    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name='{self.name}', status={self.status})>"

