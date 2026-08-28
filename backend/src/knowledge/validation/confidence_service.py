"""
Confidence Scoring Service

Calculates multi-dimensional confidence scores for extracted knowledge.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.core.logging import logger


@dataclass
class ConfidenceScore:
    """Confidence score with breakdown."""
    overall: float  # 0.0 to 1.0
    extraction: float  # Extraction confidence
    consistency: float  # Internal consistency
    citation: float  # Citation coverage
    semantic: float  # Semantic validity
    sources: Dict[str, float]  # Individual source scores


class ConfidenceScoringService(BaseValidationService):
    """
    Calculates multi-dimensional confidence scores.
    
    Unlike simple confidence scores, this service provides:
    - Extraction confidence
    - Consistency confidence
    - Citation confidence
    - Semantic confidence
    - Overall weighted confidence
    """
    
    service_name = "confidence_scoring"
    estimated_time_ms = 2000
    
    # Weights for overall confidence
    WEIGHTS = {
        "extraction": 0.30,
        "consistency": 0.25,
        "citation": 0.25,
        "semantic": 0.20
    }
    
    def __init__(self, db: Session):
        """
        Initialize the confidence scoring service.
        
        Args:
            db: Database session
        """
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Confidence service doesn't validate - it scores."""
        return ValidationResult(success=True, passed=True)
    
    def calculate_confidence(
        self,
        document_id: int,
        knowledge_type: str,
        knowledge_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceScore:
        """
        Calculate confidence score for extracted knowledge.
        
        Args:
            document_id: Source document ID
            knowledge_type: Type of knowledge
            knowledge_data: Extracted knowledge data
            context: Additional context for scoring
            
        Returns:
            ConfidenceScore with breakdown
        """
        # Calculate individual scores
        extraction_confidence = self._calculate_extraction_confidence(knowledge_data)
        consistency_confidence = self._calculate_consistency_confidence(knowledge_data)
        citation_confidence = self._calculate_citation_confidence(document_id, knowledge_type, knowledge_data)
        semantic_confidence = self._calculate_semantic_confidence(knowledge_data)
        
        # Calculate overall weighted confidence
        overall = (
            extraction_confidence * self.WEIGHTS["extraction"] +
            consistency_confidence * self.WEIGHTS["consistency"] +
            citation_confidence * self.WEIGHTS["citation"] +
            semantic_confidence * self.WEIGHTS["semantic"]
        )
        
        return ConfidenceScore(
            overall=overall,
            extraction=extraction_confidence,
            consistency=consistency_confidence,
            citation=citation_confidence,
            semantic=semantic_confidence,
            sources={
                "extraction": extraction_confidence,
                "consistency": consistency_confidence,
                "citation": citation_confidence,
                "semantic": semantic_confidence
            }
        )
    
    def _calculate_extraction_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate extraction confidence based on data quality."""
        if not data:
            return 0.0
        
        score = 0.5  # Base score
        
        # Check for required fields
        if data.get("name") or data.get("question_text") or data.get("front"):
            score += 0.2
        
        # Check for description
        if data.get("description") or data.get("answer") or data.get("back"):
            score += 0.15
        
        # Check for additional metadata
        if data.get("importance") or data.get("difficulty"):
            score += 0.1
        
        # Check for confidence from LLM
        if data.get("confidence_score"):
            llm_confidence = float(data.get("confidence_score", 0.5))
            score = score * 0.5 + llm_confidence * 0.5
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_consistency_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate consistency based on internal coherence."""
        score = 0.7  # Base score
        
        # Check for contradictory information
        if self._has_contradictions(data):
            score -= 0.3
        
        # Check for complete information
        if data.get("related_concepts") and len(data.get("related_concepts", [])) > 0:
            score += 0.1
        
        # Check for proper categorization
        if data.get("type") or data.get("entity_type") or data.get("topic_type"):
            score += 0.1
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_citation_confidence(
        self,
        document_id: int,
        knowledge_type: str,
        data: Dict[str, Any]
    ) -> float:
        """Calculate citation confidence based on source references."""
        # Check if we have citation data
        citations = data.get("citations", [])
        
        if not citations:
            # No citations - lower confidence
            return 0.3
        
        # Calculate based on citation count and quality
        score = min(len(citations) * 0.15 + 0.4, 0.9)
        
        # Check for primary citation
        has_primary = any(c.get("is_primary", False) for c in citations)
        if has_primary:
            score += 0.1
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_semantic_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate semantic validity."""
        score = 0.7  # Base score
        
        # Check for meaningful content
        text_fields = [
            data.get("description", ""),
            data.get("question_text", ""),
            data.get("front", ""),
            data.get("back", "")
        ]
        
        meaningful_content = any(len(str(t)) > 50 for t in text_fields if t)
        if meaningful_content:
            score += 0.15
        
        # Check for proper formatting
        if self._is_well_formed(data):
            score += 0.1
        
        # Penalize empty or too short content
        total_length = sum(len(str(t)) for t in text_fields if t)
        if total_length < 20:
            score -= 0.3
        
        return min(max(score, 0.0), 1.0)
    
    def _has_contradictions(self, data: Dict[str, Any]) -> bool:
        """Check for internal contradictions."""
        # Simple check for contradictory data
        return False  # Placeholder for more sophisticated check
    
    def _is_well_formed(self, data: Dict[str, Any]) -> bool:
        """Check if data is well-formed."""
        required_fields = {
            "entity": ["name", "entity_type"],
            "concept": ["name"],
            "relationship": ["source_name", "target_name", "relationship_type"],
            "question": ["question_text"],
            "flashcard": ["front", "back"]
        }
        
        knowledge_type = data.get("knowledge_type", "")
        fields = required_fields.get(knowledge_type, ["name"])
        
        return all(data.get(f) for f in fields)
    
    def calculate_document_confidence(
        self,
        document_id: int,
        entity_count: int,
        concept_count: int,
        relationship_count: int,
        citation_count: int
    ) -> float:
        """Calculate overall document confidence."""
        # Base on coverage
        if entity_count + concept_count + relationship_count == 0:
            return 0.0
        
        # Weighted average of extraction counts
        extraction_score = (
            entity_count * 0.4 +
            concept_count * 0.3 +
            relationship_count * 0.3
        )
        
        # Citation coverage
        citation_score = min(citation_count / max(entity_count + concept_count, 1), 1.0)
        
        # Combined score
        overall = extraction_score * 0.7 + citation_score * 0.3
        
        return min(overall, 1.0)
