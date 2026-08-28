"""
Evidence Service

Collects, validates, and ranks evidence for research.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.research.models import (
    ResearchEvidence, ResearchProject, EvidenceSource, ValidationConfidence
)
from src.core.logging import logger


class EvidenceService:
    """
    Service for collecting and managing research evidence.
    
    Handles:
    - Evidence collection from various sources
    - Source verification
    - Evidence ranking
    - Relevance scoring
    """
    
    def __init__(self, db: Session):
        """Initialize the evidence service."""
        self.db = db
    
    def add_evidence(
        self,
        project_id: int,
        title: str,
        content: str,
        source_type: str,
        source_url: Optional[str] = None,
        source_name: Optional[str] = None,
        author: Optional[str] = None,
        summary: Optional[str] = None,
        task_id: Optional[int] = None,
        linked_document_id: Optional[int] = None
    ) -> ResearchEvidence:
        """
        Add evidence to a research project.
        
        Args:
            project_id: Research project ID
            title: Evidence title
            content: Evidence content
            source_type: Type of source
            source_url: Source URL
            source_name: Name of source
            author: Author
            summary: Summary
            task_id: Related task
            linked_document_id: Linked workspace document
            
        Returns:
            Created evidence
        """
        evidence = ResearchEvidence(
            project_id=project_id,
            task_id=task_id,
            title=title,
            content=content,
            summary=summary or content[:500],
            source_type=source_type,
            source_url=source_url,
            source_name=source_name,
            author=author,
            linked_document_id=linked_document_id,
            retrieval_timestamp=datetime.utcnow()
        )
        
        # Calculate initial scores
        evidence.authority_score = self._calculate_authority_score(source_type, source_name)
        evidence.freshness_score = self._calculate_freshness_score(evidence.published_date)
        evidence.validation_confidence = self._determine_validation_confidence(evidence)
        evidence.overall_score = self._calculate_overall_score(evidence)
        
        self.db.add(evidence)
        
        # Update project evidence count
        project = self.db.query(ResearchProject).filter(
            ResearchProject.id == project_id
        ).first()
        
        if project:
            project.evidence_count = (project.evidence_count or 0) + 1
            project.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(evidence)
        
        logger.info(f"Added evidence {evidence.id} to project {project_id}")
        
        return evidence
    
    def _calculate_authority_score(
        self,
        source_type: str,
        source_name: Optional[str] = None
    ) -> float:
        """Calculate authority score based on source type."""
        authority_map = {
            EvidenceSource.WORKSPACE.value: 0.9,
            EvidenceSource.DOCUMENTATION.value: 0.85,
            EvidenceSource.ARXIV.value: 0.9,
            EvidenceSource.DOI.value: 0.9,
            EvidenceSource.GITHUB.value: 0.7,
            EvidenceSource.WEB_PAGE.value: 0.5,
            EvidenceSource.BLOG.value: 0.4,
            EvidenceSource.VIDEO.value: 0.5,
            EvidenceSource.USER_UPLOAD.value: 0.6,
        }
        
        base_score = authority_map.get(source_type, 0.5)
        
        # Boost for known authoritative sources
        if source_name:
            high_authority = ["openai", "google", "microsoft", "arxiv", "github", "wikipedia"]
            if any(ha in source_name.lower() for ha in high_authority):
                base_score = min(base_score + 0.1, 1.0)
        
        return base_score
    
    def _calculate_freshness_score(
        self,
        published_date: Optional[datetime] = None
    ) -> float:
        """Calculate freshness score based on publication date."""
        if not published_date:
            return 0.5  # Unknown date
        
        now = datetime.utcnow()
        age_days = (now - published_date).days
        
        if age_days < 30:
            return 1.0
        elif age_days < 180:
            return 0.9
        elif age_days < 365:
            return 0.8
        elif age_days < 730:
            return 0.6
        elif age_days < 1825:
            return 0.4
        else:
            return 0.2
    
    def _determine_validation_confidence(
        self,
        evidence: ResearchEvidence
    ) -> str:
        """Determine validation confidence level."""
        score = (
            (evidence.authority_score or 0.5) * 0.4 +
            (evidence.freshness_score or 0.5) * 0.3 +
            (evidence.popularity_score or 0.5) * 0.3
        )
        
        if score >= 0.8:
            return ValidationConfidence.HIGH.value
        elif score >= 0.6:
            return ValidationConfidence.MEDIUM.value
        elif score >= 0.4:
            return ValidationConfidence.LOW.value
        else:
            return ValidationConfidence.UNKNOWN.value
    
    def _calculate_overall_score(
        self,
        evidence: ResearchEvidence
    ) -> float:
        """Calculate overall evidence score."""
        authority = evidence.authority_score or 0.5
        freshness = evidence.freshness_score or 0.5
        popularity = evidence.popularity_score or 0.5
        relevance = evidence.relevance_score or 0.5
        credibility = evidence.credibility_score or 0.5
        
        weights = {
            "relevance": 0.30,
            "credibility": 0.25,
            "authority": 0.20,
            "freshness": 0.15,
            "popularity": 0.10
        }
        
        overall = (
            relevance * weights["relevance"] +
            credibility * weights["credibility"] +
            authority * weights["authority"] +
            freshness * weights["freshness"] +
            popularity * weights["popularity"]
        )
        
        return round(overall, 3)
    
    def update_relevance_score(
        self,
        evidence_id: int,
        relevance_score: float
    ) -> ResearchEvidence:
        """Update evidence relevance score and recalculate overall."""
        evidence = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.id == evidence_id
        ).first()
        
        if not evidence:
            raise ValueError(f"Evidence {evidence_id} not found")
        
        evidence.relevance_score = relevance_score
        evidence.overall_score = self._calculate_overall_score(evidence)
        
        self.db.commit()
        self.db.refresh(evidence)
        
        return evidence
    
    def rank_evidence(
        self,
        project_id: int,
        query: Optional[str] = None,
        limit: int = 20
    ) -> List[ResearchEvidence]:
        """
        Rank evidence for a project.
        
        Args:
            project_id: Project ID
            query: Optional search query
            limit: Maximum results
            
        Returns:
            Ranked list of evidence
        """
        evidence_list = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.project_id == project_id,
            ResearchEvidence.is_pertinent == True
        ).order_by(
            ResearchEvidence.overall_score.desc()
        ).limit(limit).all()
        
        return evidence_list
    
    def get_evidence_for_task(
        self,
        task_id: int
    ) -> List[ResearchEvidence]:
        """Get all evidence for a task."""
        return self.db.query(ResearchEvidence).filter(
            ResearchEvidence.task_id == task_id
        ).order_by(
            ResearchEvidence.overall_score.desc()
        ).all()
    
    def validate_evidence(
        self,
        evidence_id: int,
        is_validated: bool = True
    ) -> ResearchEvidence:
        """Mark evidence as validated."""
        evidence = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.id == evidence_id
        ).first()
        
        if not evidence:
            raise ValueError(f"Evidence {evidence_id} not found")
        
        evidence.is_validated = is_validated
        
        self.db.commit()
        self.db.refresh(evidence)
        
        return evidence
    
    def mark_as_pertinent(
        self,
        evidence_id: int,
        is_pertinent: bool = True
    ) -> ResearchEvidence:
        """Mark evidence as pertinent to research."""
        evidence = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.id == evidence_id
        ).first()
        
        if not evidence:
            raise ValueError(f"Evidence {evidence_id} not found")
        
        evidence.is_pertinent = is_pertinent
        
        self.db.commit()
        self.db.refresh(evidence)
        
        return evidence
    
    def get_confidence_breakdown(
        self,
        evidence_id: int
    ) -> Dict[str, float]:
        """Get confidence score breakdown."""
        evidence = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.id == evidence_id
        ).first()
        
        if not evidence:
            raise ValueError(f"Evidence {evidence_id} not found")
        
        return {
            "authority_score": evidence.authority_score or 0,
            "freshness_score": evidence.freshness_score or 0,
            "popularity_score": evidence.popularity_score or 0,
            "relevance_score": evidence.relevance_score or 0,
            "credibility_score": evidence.credibility_score or 0,
            "overall_score": evidence.overall_score or 0,
            "validation_confidence": evidence.validation_confidence
        }
    
    def import_from_workspace(
        self,
        project_id: int,
        document_id: int,
        task_id: Optional[int] = None
    ) -> ResearchEvidence:
        """Import evidence from workspace document."""
        from src.models.document import Document
        from src.knowledge.models import DocumentSummary
        
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get summary if available
        summary = self.db.query(DocumentSummary).filter(
            DocumentSummary.document_id == document_id
        ).first()
        
        content = ""
        if summary:
            content = summary.executive_summary or summary.detailed_summary or ""
        
        evidence = self.add_evidence(
            project_id=project_id,
            title=document.title or document.original_filename,
            content=content or "Document content",
            source_type=EvidenceSource.WORKSPACE.value,
            source_name="Workspace Document",
            task_id=task_id,
            linked_document_id=document_id
        )
        
        # Mark as highly trusted
        evidence.workspace_trust = True
        evidence.validation_confidence = ValidationConfidence.HIGH.value
        evidence.authority_score = 0.95
        evidence.overall_score = self._calculate_overall_score(evidence)
        
        self.db.commit()
        
        return evidence
