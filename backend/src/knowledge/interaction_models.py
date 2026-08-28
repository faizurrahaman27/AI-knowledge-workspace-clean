"""
Knowledge Interaction Models

Database models for the AI Notebook, Collections, and user interactions.
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


class NoteType(str, Enum):
    """Types of notes."""
    USER = "user"
    AI_RESPONSE = "ai_response"
    SUMMARY = "summary"
    CONCEPT = "concept"
    STUDY_GUIDE = "study_guide"
    BOOKMARK = "bookmark"


class CollectionType(str, Enum):
    """Types of collections."""
    FOLDER = "folder"
    TOPIC = "topic"
    PROJECT = "project"
    COURSE = "course"
    CUSTOM = "custom"


# ============================================================================
# AI Notebook
# ============================================================================

class KnowledgeNote(Base):
    """
    AI Notebook for storing user and AI notes.
    
    Notes are linked to validated knowledge.
    """
    __tablename__ = "knowledge_notes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Content
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default=NoteType.USER.value)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Optional references
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    
    # Source knowledge (if derived)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_concept_id = Column(Integer, nullable=True)
    source_question_id = Column(Integer, ForeignKey("generated_questions.id", ondelete="SET NULL"), nullable=True)
    source_flashcard_id = Column(Integer, ForeignKey("knowledge_flashcards.id", ondelete="SET NULL"), nullable=True)
    
    # AI metadata
    ai_generated = Column(Boolean, default=False)
    ai_model = Column(String(100), nullable=True)
    ai_provider = Column(String(100), nullable=True)
    
    # Citations (linked knowledge)
    citations = Column(JSON, nullable=True)  # [{type, id, name}]
    
    # Formatting
    format_type = Column(String(20), default="markdown")  # markdown, latex, code
    
    # State
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
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

    # Relationships
    user = relationship("User")
    workspace = relationship("Workspace")
    document = relationship("Document")

    __table_args__ = (
        Index('ix_notes_user', 'user_id'),
        Index('ix_notes_workspace', 'workspace_id'),
        Index('ix_notes_type', 'note_type'),
        Index('ix_notes_created', 'created_at'),
    )


# ============================================================================
# Collections
# ============================================================================

class KnowledgeCollection(Base):
    """
    User collections for organizing knowledge.
    
    Collections can contain documents, notes, flashcards, questions, etc.
    """
    __tablename__ = "knowledge_collections"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    collection_type = Column(String(50), default=CollectionType.FOLDER.value)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=True)
    
    # Metadata
    color = Column(String(20), nullable=True)  # hex color
    icon = Column(String(50), nullable=True)  # emoji or icon name
    tags = Column(JSON, nullable=True)  # ["machine-learning", "ai"]
    
    # Settings
    is_public = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    
    # Timestamps
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
    user = relationship("User", back_populates="collections")
    parent = relationship("KnowledgeCollection", remote_side=[id], backref="children")
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_collections_user', 'user_id'),
        Index('ix_collections_parent', 'parent_id'),
        Index('ix_collections_type', 'collection_type'),
    )


class CollectionItem(Base):
    """
    Items within a collection.
    """
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Collection
    collection_id = Column(Integer, ForeignKey("knowledge_collections.id", ondelete="CASCADE"), nullable=False)
    
    # Item reference
    item_type = Column(String(50), nullable=False)  # document, note, flashcard, question, concept, summary
    item_id = Column(Integer, nullable=False)
    
    # Order
    order_index = Column(Integer, default=0)
    
    # Metadata
    notes = Column(Text, nullable=True)  # User notes about this item
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    collection = relationship("KnowledgeCollection", back_populates="items")

    __table_args__ = (
        Index('ix_collection_items_collection', 'collection_id'),
        Index('ix_collection_items_type_id', 'item_type', 'item_id'),
        UniqueConstraint('collection_id', 'item_type', 'item_id', name='uq_collection_item'),
    )


# ============================================================================
# Bookmarks
# ============================================================================

class KnowledgeBookmark(Base):
    """
    Bookmarks for quick access to knowledge items.
    """
    __tablename__ = "knowledge_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Item reference
    item_type = Column(String(50), nullable=False)  # document, note, flashcard, question, etc.
    item_id = Column(Integer, nullable=False)
    
    # Bookmark metadata
    title = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    position = Column(Integer, nullable=True)  # Position in bookmark list
    
    # Collection (optional)
    collection_id = Column(Integer, ForeignKey("knowledge_collections.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    collection = relationship("KnowledgeCollection")

    __table_args__ = (
        Index('ix_bookmarks_user', 'user_id'),
        Index('ix_bookmarks_collection', 'collection_id'),
        Index('ix_bookmarks_item', 'item_type', 'item_id'),
    )


# ============================================================================
# Pinned Items
# ============================================================================

class PinnedItem(Base):
    """
    Pinned items for quick access.
    """
    __tablename__ = "pinned_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Item reference
    item_type = Column(String(50), nullable=False)
    item_id = Column(Integer, nullable=False)
    
    # Pin metadata
    pin_type = Column(String(50), default="pin")  # pin, favorite, star
    title = Column(String(500), nullable=True)
    thumbnail = Column(String(500), nullable=True)  # Preview image URL
    
    # Workspace context
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    workspace = relationship("Workspace")

    __table_args__ = (
        Index('ix_pinned_user', 'user_id'),
        Index('ix_pinned_workspace', 'workspace_id'),
        UniqueConstraint('user_id', 'item_type', 'item_id', name='uq_pinned_item'),
    )


# ============================================================================
# Recent Activity
# ============================================================================

class RecentActivity(Base):
    """
    Tracks recent user activity for dashboard.
    """
    __tablename__ = "recent_activity"

    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Activity
    activity_type = Column(String(50), nullable=False)  # opened, generated, studied, uploaded
    item_type = Column(String(50), nullable=False)  # document, note, flashcard, etc.
    item_id = Column(Integer, nullable=False)
    
    # Metadata
    title = Column(String(500), nullable=True)
    preview = Column(Text, nullable=True)  # Preview text
    
    # Workspace context
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    workspace = relationship("Workspace")

    __table_args__ = (
        Index('ix_recent_user', 'user_id'),
        Index('ix_recent_created', 'created_at'),
        Index('ix_recent_type', 'activity_type', 'item_type'),
    )


# ============================================================================
# Workspace Layout
# ============================================================================

class WorkspaceLayout(Base):
    """
    Stores user workspace layout preferences.
    """
    __tablename__ = "workspace_layouts"

    id = Column(Integer, primary_key=True, index=True)
    
    # User & Workspace
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    
    # Layout configuration
    layout_name = Column(String(100), default="default")
    layout_config = Column(JSON, nullable=False)  # {left: {width, visible}, center: {...}, right: {...}}
    
    # Panel states
    panel_states = Column(JSON, nullable=True)  # {notebook: {open, height}, explorer: {...}}
    
    # Active items
    active_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    active_note_id = Column(Integer, ForeignKey("knowledge_notes.id", ondelete="SET NULL"), nullable=True)
    
    # Theme
    theme = Column(String(20), default="dark")
    
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="workspace_layouts"
    )
    workspace = relationship("Workspace")
    document = relationship("Document")

    __table_args__ = (
        Index('ix_layout_user', 'user_id'),
        Index('ix_layout_workspace', 'workspace_id'),
        UniqueConstraint('user_id', 'workspace_id', name='uq_user_workspace_layout'),
    )


# ============================================================================
# Update existing models with interaction references
# ============================================================================

# Note: User model should have a collections relationship
# Note: Workspace model should track active knowledge state
