"""
Audit Service

Manages audit logs for knowledge processing operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.knowledge.validation_models import KnowledgeAudit, AuditEventType
from src.core.logging import logger


class AuditService(BaseValidationService):
    """
    Manages audit logs for all knowledge processing operations.
    
    Tracks:
    - Extraction events
    - Validation events
    - Modification events
    - System events
    """
    
    service_name = "audit"
    estimated_time_ms = 100
    
    def __init__(self, db: Session):
        """Initialize the audit service."""
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Audit doesn't validate."""
        return ValidationResult(success=True, passed=True)
    
    def log_event(
        self,
        event_type: AuditEventType,
        description: str,
        document_id: Optional[int] = None,
        knowledge_type: Optional[str] = None,
        knowledge_id: Optional[int] = None,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        action: str = "create",
        previous_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        service_name: Optional[str] = None,
        processing_duration_ms: Optional[int] = None
    ) -> KnowledgeAudit:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            description: Human-readable description
            document_id: Optional document ID
            knowledge_type: Optional knowledge type
            knowledge_id: Optional knowledge item ID
            actor_type: Actor type (system, user, api)
            actor_id: Actor identifier
            action: Action (create, update, delete, merge)
            previous_value: Value before change
            new_value: Value after change
            metadata: Additional metadata
            service_name: Service that generated the event
            processing_duration_ms: Processing time
            
        Returns:
            Created audit record
        """
        audit = KnowledgeAudit(
            document_id=document_id,
            event_type=event_type.value if isinstance(event_type, AuditEventType) else event_type,
            knowledge_type=knowledge_type,
            knowledge_id=knowledge_id,
            description=description,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            previous_value=previous_value,
            new_value=new_value,
            metadata=metadata,
            service_name=service_name,
            processing_duration_ms=processing_duration_ms,
        )
        
        self.db.add(audit)
        self.db.commit()
        
        return audit
    
    def log_extraction_started(
        self,
        document_id: int,
        processing_info: Dict[str, Any]
    ) -> KnowledgeAudit:
        """Log extraction started event."""
        return self.log_event(
            event_type=AuditEventType.EXTRACTION_STARTED,
            description=f"Knowledge extraction started for document {document_id}",
            document_id=document_id,
            metadata=processing_info,
            service_name="knowledge_extraction"
        )
    
    def log_extraction_completed(
        self,
        document_id: int,
        item_counts: Dict[str, int]
    ) -> KnowledgeAudit:
        """Log extraction completed event."""
        return self.log_event(
            event_type=AuditEventType.EXTRACTION_COMPLETED,
            description=f"Knowledge extraction completed for document {document_id}",
            document_id=document_id,
            metadata=item_counts,
            service_name="knowledge_extraction"
        )
    
    def log_validation_started(
        self,
        document_id: int
    ) -> KnowledgeAudit:
        """Log validation started event."""
        return self.log_event(
            event_type=AuditEventType.VALIDATION_STARTED,
            description=f"Validation started for document {document_id}",
            document_id=document_id,
            service_name="knowledge_validation"
        )
    
    def log_validation_completed(
        self,
        document_id: int,
        validation_results: Dict[str, Any]
    ) -> KnowledgeAudit:
        """Log validation completed event."""
        return self.log_event(
            event_type=AuditEventType.VALIDATION_COMPLETED,
            description=f"Validation completed for document {document_id}",
            document_id=document_id,
            metadata=validation_results,
            service_name="knowledge_validation"
        )
    
    def log_entity_merged(
        self,
        document_id: int,
        source_id: int,
        target_id: int,
        merged_name: str
    ) -> KnowledgeAudit:
        """Log entity merge event."""
        return self.log_event(
            event_type=AuditEventType.ENTITY_MERGED,
            description=f"Entity merged: {merged_name}",
            document_id=document_id,
            knowledge_type="entity",
            knowledge_id=target_id,
            action="merge",
            previous_value={"entity_id": source_id},
            new_value={"entity_id": target_id, "canonical_name": merged_name},
            service_name="entity_resolution"
        )
    
    def log_duplicate_removed(
        self,
        document_id: int,
        knowledge_type: str,
        item_id: int,
        kept_item_id: int
    ) -> KnowledgeAudit:
        """Log duplicate removal event."""
        return self.log_event(
            event_type=AuditEventType.DUPLICATE_REMOVED,
            description=f"Duplicate {knowledge_type} removed",
            document_id=document_id,
            knowledge_type=knowledge_type,
            knowledge_id=item_id,
            action="delete",
            previous_value={"item_id": item_id},
            new_value={"kept_item_id": kept_item_id},
            service_name="duplicate_detection"
        )
    
    def log_quality_calculated(
        self,
        document_id: int,
        quality_score: float,
        confidence_score: float
    ) -> KnowledgeAudit:
        """Log quality score calculation."""
        return self.log_event(
            event_type=AuditEventType.QUALITY_SCORE_CALCULATED,
            description=f"Quality score calculated: {quality_score:.2f}",
            document_id=document_id,
            metadata={
                "quality_score": quality_score,
                "confidence_score": confidence_score
            },
            service_name="quality_scoring"
        )
    
    def get_audit_history(
        self,
        document_id: int,
        limit: int = 100,
        event_types: Optional[List[str]] = None
    ) -> List[KnowledgeAudit]:
        """
        Get audit history for a document.
        
        Args:
            document_id: Document ID
            limit: Maximum records to return
            event_types: Optional filter by event types
            
        Returns:
            List of audit records
        """
        query = self.db.query(KnowledgeAudit).filter(
            KnowledgeAudit.document_id == document_id
        )
        
        if event_types:
            query = query.filter(KnowledgeAudit.event_type.in_(event_types))
        
        return query.order_by(
            KnowledgeAudit.created_at.desc()
        ).limit(limit).all()
    
    def get_recent_audits(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[KnowledgeAudit]:
        """Get recent audit events across all documents."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(KnowledgeAudit).filter(
            KnowledgeAudit.created_at >= cutoff
        ).order_by(
            KnowledgeAudit.created_at.desc()
        ).limit(limit).all()
    
    def get_audits_for_knowledge(
        self,
        knowledge_type: str,
        knowledge_id: int,
        limit: int = 50
    ) -> List[KnowledgeAudit]:
        """Get audit history for a specific knowledge item."""
        return self.db.query(KnowledgeAudit).filter(
            KnowledgeAudit.knowledge_type == knowledge_type,
            KnowledgeAudit.knowledge_id == knowledge_id
        ).order_by(
            KnowledgeAudit.created_at.desc()
        ).limit(limit).all()
    
    def search_audits(
        self,
        query: str,
        limit: int = 100
    ) -> List[KnowledgeAudit]:
        """Search audit logs by description."""
        return self.db.query(KnowledgeAudit).filter(
            KnowledgeAudit.description.ilike(f"%{query}%")
        ).order_by(
            KnowledgeAudit.created_at.desc()
        ).limit(limit).all()
