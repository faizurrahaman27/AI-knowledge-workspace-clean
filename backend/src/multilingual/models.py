"""
Multilingual Intelligence Models

Database models for multilingual support.
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


class WritingDirection(str, Enum):
    """Writing direction values."""
    LTR = "ltr"
    RTL = "rtl"
    MIXED = "mixed"


class ScriptType(str, Enum):
    """Script types for languages."""
    LATIN = "latin"
    ARABIC = "arabic"
    CYRILLIC = "cyrillic"
    DEVANAGARI = "devanagari"
    CJK = "cjk"  # Chinese, Japanese, Korean
    TAMIL = "tamil"
    TELUGU = "telugu"
    HEBREW = "hebrew"
    GEORGIAN = "georgian"
    GREEK = "greek"
    THAI = "thai"
    OTHER = "other"


# ============================================================================
# Supported Languages
# ============================================================================

class Language(Base):
    """
    Supported language in the system.
    """
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, index=True)
    
    # ISO codes
    code = Column(String(10), unique=True, nullable=False)  # e.g., "en", "ar", "zh"
    iso_name = Column(String(100), nullable=False)  # e.g., "English", "Arabic"
    native_name = Column(String(100), nullable=False)  # e.g., "English", "العربية"
    
    # Script
    script_type = Column(String(20), nullable=False)
    writing_direction = Column(String(10), default=WritingDirection.LTR.value)
    
    # Support flags
    has_ocr_support = Column(Boolean, default=False)
    has_embeddings = Column(Boolean, default=False)
    has_tts = Column(Boolean, default=False)
    
    # NLP settings
    word_tokenizer = Column(String(50), nullable=True)
    sentence_tokenizer = Column(String(50), nullable=True)
    stemmer = Column(String(50), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_rtl = Column(Boolean, default=False)
    nlp_priority = Column(Integer, default=5)
    
    # Character set
    characters = Column(Text, nullable=True)  # Character set for validation
    
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
        Index('ix_languages_code', 'code', unique=True),
        Index('ix_languages_script', 'script_type'),
    )


# ============================================================================
# User Language Preferences
# ============================================================================

class LanguagePreference(Base):
    """
    User language preferences.
    """
    __tablename__ = "language_preferences"

    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Preference mode
    preference_mode = Column(String(50), default="auto")  # auto, english, arabic, etc.
    follow_upload_language = Column(Boolean, default=True)
    follow_query_language = Column(Boolean, default=True)
    
    # Always use language (overrides auto)
    preferred_output_language = Column(String(10), nullable=True)
    
    # UI language
    ui_language = Column(String(10), default="en")
    
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
    user = relationship("User")

    __table_args__ = (
        Index('ix_pref_user', 'user_id', unique=True),
    )


# ============================================================================
# Document Languages
# ============================================================================

class DocumentLanguage(Base):
    """
    Detected language for a document.
    """
    __tablename__ = "document_languages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Document
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Detected language
    primary_language = Column(String(10), nullable=False)
    language_confidence = Column(Float, default=0.0)
    
    # Additional info
    script_type = Column(String(20), nullable=True)
    writing_direction = Column(String(10), default=WritingDirection.LTR.value)
    is_mixed_language = Column(Boolean, default=False)
    
    # Secondary languages (for mixed docs)
    secondary_languages = Column(JSON, nullable=True)  # [{"lang": "en", "confidence": 0.3}]
    
    # Character encoding
    detected_encoding = Column(String(50), nullable=True)
    
    # Detection metadata
    detection_method = Column(String(50), nullable=True)  # fasttext, langdetect, etc.
    confidence_breakdown = Column(JSON, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_doclang_document', 'document_id', unique=True),
        Index('ix_doclang_language', 'primary_language'),
    )


# ============================================================================
# Chunk Languages
# ============================================================================

class ChunkLanguage(Base):
    """
    Language information for document chunks.
    """
    __tablename__ = "chunk_languages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Chunk
    chunk_id = Column(Integer, nullable=False)  # References document_chunks table
    
    # Document
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Language
    language = Column(String(10), nullable=False)
    confidence = Column(Float, default=0.0)
    is_primary = Column(Boolean, default=True)
    
    # Normalized text
    normalized_text = Column(Text, nullable=True)
    original_text_length = Column(Integer, default=0)
    normalized_text_length = Column(Integer, default=0)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    document = relationship("Document")

    __table_args__ = (
        Index('ix_chunklang_chunk', 'chunk_id'),
        Index('ix_chunklang_document', 'document_id'),
    )


# ============================================================================
# Translation Cache
# ============================================================================

class TranslationCache(Base):
    """
    Cache for translations to avoid redundant API calls.
    """
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True)
    
    # Source and target
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    
    # Content hashes
    source_text_hash = Column(String(64), nullable=False)
    source_text_length = Column(Integer, default=0)
    
    # Translation
    translated_text = Column(Text, nullable=False)
    translation_model = Column(String(100), nullable=True)
    
    # Quality
    quality_score = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False)
    
    # Usage
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
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
        Index('ix_trans_cache_lookup', 'source_language', 'target_language', 'source_text_hash', unique=True),
        Index('ix_trans_cache_usage', 'usage_count'),
    )


# ============================================================================
# Cross-Language Mappings
# ============================================================================

class CrossLanguageMapping(Base):
    """
    Cross-language concept/entity mappings.
    """
    __tablename__ = "cross_language_mappings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Concept
    concept_id = Column(Integer, nullable=True)
    entity_id = Column(Integer, nullable=True)
    
    # Mappings
    mappings = Column(JSON, nullable=False)  # {"en": "machine learning", "ar": "تعلم الآلة", "zh": "机器学习", ...}
    
    # Confidence
    confidence = Column(Float, default=1.0)
    
    # Source
    source_type = Column(String(50), nullable=True)  # ai_generated, verified, external
    
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
        Index('ix_xling_concept', 'concept_id'),
        Index('ix_xling_entity', 'entity_id'),
    )


# ============================================================================
# Language Metrics
# ============================================================================

class LanguageMetric(Base):
    """
    Metrics for language processing.
    """
    __tablename__ = "language_metrics"

    id = Column(Integer, primary_key=True, index=True)
    
    # User and document
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    
    # Metrics type
    metric_type = Column(String(50), nullable=False)  # detection, ocr, embedding, retrieval, generation
    
    # Language
    language = Column(String(10), nullable=True)
    
    # Metrics values
    accuracy = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, default=False)
    
    # Additional data
    processing_metadata = Column(JSON, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    __table_args__ = (
        Index('ix_langmet_user', 'user_id'),
        Index('ix_langmet_type', 'metric_type'),
        Index('ix_langmet_language', 'language'),
    )
