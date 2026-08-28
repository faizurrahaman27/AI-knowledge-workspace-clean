"""
Conflict Detection Service

Detects and manages conflicts between evidence.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from sqlalchemy.orm import Session

from src.research.models import (
    ResearchConflict, ResearchEvidence
)
from src.core.logging import logger


class ConflictDetectionService:
    """
    Service for detecting and managing conflicts between evidence.
    """
    
    def __init__(self, db: Session):
        """Initialize the conflict detection service."""
        self.db = db
    
    def detect_conflicts(self, project_id: int) -> List[ResearchConflict]:
        """Detect all conflicts in a project."""
        evidence_list = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.project_id == project_id,
            ResearchEvidence.is_pertinent == True
        ).all()
        
        conflicts = []
        
        for i in range(len(evidence_list)):
            for j in range(i + 1, len(evidence_list)):
                conflict = self._compare_evidence(evidence_list[i], evidence_list[j])
                if conflict:
                    self.db.add(conflict)
                    conflicts.append(conflict)
        
        self.db.commit()
        logger.info(f"Detected {len(conflicts)} conflicts in project {project_id}")
        return conflicts
    
    def _compare_evidence(self, evidence_a: ResearchEvidence, evidence_b: ResearchEvidence) -> Optional[ResearchConflict]:
        """Compare two evidence items for conflicts."""
        # Check for contradictory phrases
        content_a = (evidence_a.summary or evidence_a.content or "").lower()
        content_b = (evidence_b.summary or evidence_b.content or "").lower()
        
        contradictions = [
            (["is not", "isn't", "aren't", "doesn't", "cannot", "won't"], ["is", "does", "can", "will"])
        ]
        
        for neg_words, pos_words in contradictions:
            neg_a = any(nw in content_a for nw in neg_words)
            pos_a = any(pw in content_a for pw in pos_words)
            neg_b = any(nw in content_b for nw in neg_words)
            pos_b = any(pw in content_b for pw in pos_words)
            
            if (pos_a and neg_b and not neg_a) or (pos_b and neg_a and not neg_b):
                return ResearchConflict(
                    project_id=evidence_a.project_id,
                    conflict_type="claim",
                    description=f"Contradictory claims between '{evidence_a.title}' and '{evidence_b.title}'",
                    evidence_a_id=evidence_a.id,
                    evidence_b_id=evidence_b.id
                )
        
        return None
    
    def get_conflicts(self, project_id: int, conflict_type: Optional[str] = None) -> List[ResearchConflict]:
        """Get conflicts for a project."""
        query = self.db.query(ResearchConflict).filter(ResearchConflict.project_id == project_id)
        if conflict_type:
            query = query.filter(ResearchConflict.conflict_type == conflict_type)
        return query.order_by(ResearchConflict.created_at.desc()).all()
    
    def resolve_conflict(self, conflict_id: int, resolution_notes: str) -> ResearchConflict:
        """Resolve a conflict."""
        conflict = self.db.query(ResearchConflict).filter(ResearchConflict.id == conflict_id).first()
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        conflict.resolution_status = "resolved"
        conflict.resolution_notes = resolution_notes
        conflict.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conflict)
        return conflict
    
    def get_conflict_statistics(self, project_id: int) -> Dict[str, Any]:
        """Get conflict statistics."""
        conflicts = self.get_conflicts(project_id)
        type_counts = {}
        status_counts = {}
        
        for c in conflicts:
            type_counts[c.conflict_type] = type_counts.get(c.conflict_type, 0) + 1
            status_counts[c.resolution_status] = status_counts.get(c.resolution_status, 0) + 1
        
        return {
            "total": len(conflicts),
            "by_type": type_counts,
            "by_status": status_counts
        }
