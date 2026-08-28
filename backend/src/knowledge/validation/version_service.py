"""
Version Tracking Service

Manages version history of knowledge extractions.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.knowledge.validation_models import KnowledgeVersion
from src.core.logging import logger


class KnowledgeVersionService(BaseValidationService):
    """
    Manages version history of knowledge extractions.
    
    Tracks:
    - Extraction version
    - Processing details
    - Quality metrics
    - Reprocessing support
    """
    
    service_name = "version_tracking"
    estimated_time_ms = 1000
    
    CURRENT_EXTRACTION_VERSION = "1.0.0"
    
    def __init__(self, db: Session):
        """Initialize the version tracking service."""
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Version tracking doesn't validate."""
        return ValidationResult(success=True, passed=True)
    
    def create_version(
        self,
        document_id: int,
        processing_info: Dict[str, Any],
        quality_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
        changelog: Optional[str] = None
    ) -> KnowledgeVersion:
        """
        Create a new version record.
        
        Args:
            document_id: Document ID
            processing_info: Processing details
            quality_score: Overall quality score
            confidence_score: Overall confidence score
            changelog: Optional changelog
            
        Returns:
            Created version record
        """
        # Get next version number
        latest = self.get_latest_version(document_id)
        version_number = (latest.version_number + 1) if latest else 1
        
        # Mark all previous versions as not current
        if latest:
            latest.is_current = False
        
        # Create new version
        version = KnowledgeVersion(
            document_id=document_id,
            version_number=version_number,
            is_current=True,
            extraction_version=self.CURRENT_EXTRACTION_VERSION,
            llm_provider=processing_info.get("llm_provider"),
            llm_model=processing_info.get("llm_model"),
            embedding_model=processing_info.get("embedding_model"),
            processing_strategy=processing_info.get("strategy"),
            processing_duration_ms=processing_info.get("duration_ms"),
            quality_score=quality_score,
            confidence_score=confidence_score,
            extraction_timestamp=datetime.utcnow(),
            changelog=changelog,
        )
        
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        
        logger.info(f"Created version {version_number} for document {document_id}")
        
        return version
    
    def get_latest_version(self, document_id: int) -> Optional[KnowledgeVersion]:
        """Get the latest version for a document."""
        return self.db.query(KnowledgeVersion).filter(
            KnowledgeVersion.document_id == document_id,
            KnowledgeVersion.is_current == True
        ).first()
    
    def get_version_history(
        self,
        document_id: int,
        limit: int = 10
    ) -> List[KnowledgeVersion]:
        """Get version history for a document."""
        return self.db.query(KnowledgeVersion).filter(
            KnowledgeVersion.document_id == document_id
        ).order_by(
            KnowledgeVersion.version_number.desc()
        ).limit(limit).all()
    
    def get_version(
        self,
        document_id: int,
        version_number: int
    ) -> Optional[KnowledgeVersion]:
        """Get a specific version."""
        return self.db.query(KnowledgeVersion).filter(
            KnowledgeVersion.document_id == document_id,
            KnowledgeVersion.version_number == version_number
        ).first()
    
    def rollback_to_version(
        self,
        document_id: int,
        version_number: int
    ) -> bool:
        """
        Rollback to a specific version.
        
        Note: This only updates version metadata. Actual data rollback
        would require more complex implementation.
        
        Args:
            document_id: Document ID
            version_number: Version to rollback to
            
        Returns:
            True if successful
        """
        target = self.get_version(document_id, version_number)
        
        if not target:
            return False
        
        # Get current version
        current = self.get_latest_version(document_id)
        
        if current:
            current.is_current = False
        
        # Mark target as current
        target.is_current = True
        target.validation_timestamp = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Rolled back document {document_id} to version {version_number}")
        
        return True
    
    def compare_versions(
        self,
        document_id: int,
        version_a: int,
        version_b: int
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two versions.
        
        Args:
            document_id: Document ID
            version_a: First version number
            version_b: Second version number
            
        Returns:
            Comparison details
        """
        v_a = self.get_version(document_id, version_a)
        v_b = self.get_version(document_id, version_b)
        
        if not v_a or not v_b:
            return None
        
        return {
            "version_a": {
                "number": v_a.version_number,
                "quality_score": v_a.quality_score,
                "confidence_score": v_a.confidence_score,
                "extraction_timestamp": v_a.extraction_timestamp.isoformat() if v_a.extraction_timestamp else None,
                "llm_model": v_a.llm_model,
            },
            "version_b": {
                "number": v_b.version_number,
                "quality_score": v_b.quality_score,
                "confidence_score": v_b.confidence_score,
                "extraction_timestamp": v_b.extraction_timestamp.isoformat() if v_b.extraction_timestamp else None,
                "llm_model": v_b.llm_model,
            },
            "quality_diff": (v_b.quality_score or 0) - (v_a.quality_score or 0),
            "confidence_diff": (v_b.confidence_score or 0) - (v_a.confidence_score or 0),
        }
