"""
Quality Scoring Service

Calculates overall quality scores for extracted knowledge.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.knowledge.validation_models import KnowledgeQuality
from src.core.logging import logger


@dataclass
class QualityScore:
    """Quality score with component breakdown."""
    overall: float  # 0.0 to 1.0
    extraction_completeness: float
    entity_quality: float
    relationship_quality: float
    summary_quality: float
    citation_coverage: float
    topic_coverage: float
    metadata_completeness: float
    knowledge_density: float


class QualityScoringService(BaseValidationService):
    """
    Calculates overall quality scores for document knowledge.
    
    Considers:
    - Extraction completeness
    - Entity quality
    - Relationship quality
    - Summary quality
    - Citation coverage
    - Topic coverage
    - Metadata completeness
    - Knowledge density
    """
    
    service_name = "quality_scoring"
    estimated_time_ms = 3000
    
    # Weights for overall quality
    WEIGHTS = {
        "extraction_completeness": 0.15,
        "entity_quality": 0.15,
        "relationship_quality": 0.15,
        "summary_quality": 0.10,
        "citation_coverage": 0.15,
        "topic_coverage": 0.10,
        "metadata_completeness": 0.10,
        "knowledge_density": 0.10,
    }
    
    def __init__(self, db: Session):
        """Initialize the quality scoring service."""
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Quality scoring doesn't validate."""
        return ValidationResult(success=True, passed=True)
    
    def calculate_quality(
        self,
        document_id: int,
        document_stats: Dict[str, Any],
        entity_count: int,
        concept_count: int,
        relationship_count: int,
        citation_count: int,
        validation_results: list = None
    ) -> QualityScore:
        """
        Calculate overall quality score.
        
        Args:
            document_id: Document ID
            document_stats: Document statistics (word_count, etc.)
            entity_count: Number of entities
            concept_count: Number of concepts
            relationship_count: Number of relationships
            citation_count: Number of citations
            validation_results: Optional validation results
            
        Returns:
            QualityScore with breakdown
        """
        # Calculate component scores
        extraction_completeness = self._calculate_extraction_completeness(
            entity_count, concept_count, relationship_count
        )
        
        entity_quality = self._calculate_entity_quality(entity_count, citation_count)
        
        relationship_quality = self._calculate_relationship_quality(
            relationship_count, entity_count + concept_count
        )
        
        summary_quality = self._calculate_summary_quality(document_stats)
        
        citation_coverage = self._calculate_citation_coverage(
            entity_count, concept_count, citation_count
        )
        
        topic_coverage = self._calculate_topic_coverage(document_stats)
        
        metadata_completeness = self._calculate_metadata_completeness(document_stats)
        
        knowledge_density = self._calculate_knowledge_density(
            entity_count, concept_count, relationship_count,
            document_stats.get("word_count", 0)
        )
        
        # Calculate overall weighted score
        overall = sum([
            extraction_completeness * self.WEIGHTS["extraction_completeness"],
            entity_quality * self.WEIGHTS["entity_quality"],
            relationship_quality * self.WEIGHTS["relationship_quality"],
            summary_quality * self.WEIGHTS["summary_quality"],
            citation_coverage * self.WEIGHTS["citation_coverage"],
            topic_coverage * self.WEIGHTS["topic_coverage"],
            metadata_completeness * self.WEIGHTS["metadata_completeness"],
            knowledge_density * self.WEIGHTS["knowledge_density"],
        ])
        
        quality = QualityScore(
            overall=overall,
            extraction_completeness=extraction_completeness,
            entity_quality=entity_quality,
            relationship_quality=relationship_quality,
            summary_quality=summary_quality,
            citation_coverage=citation_coverage,
            topic_coverage=topic_coverage,
            metadata_completeness=metadata_completeness,
            knowledge_density=knowledge_density
        )
        
        # Save to database
        self._save_quality_score(document_id, quality, entity_count, concept_count, relationship_count, citation_count)
        
        return quality
    
    def _calculate_extraction_completeness(
        self,
        entity_count: int,
        concept_count: int,
        relationship_count: int
    ) -> float:
        """Calculate extraction completeness score."""
        total = entity_count + concept_count + relationship_count
        
        if total == 0:
            return 0.0
        
        # More items = better completeness
        # Cap at reasonable thresholds
        score = min(total / 50, 1.0)  # 50 items = perfect
        
        return score
    
    def _calculate_entity_quality(
        self,
        entity_count: int,
        citation_count: int
    ) -> float:
        """Calculate entity quality based on coverage."""
        if entity_count == 0:
            return 0.0
        
        # More entities with citations = better quality
        coverage = citation_count / entity_count
        
        # Bonus for having entities
        count_bonus = min(entity_count / 20, 0.3)
        
        return min(coverage + count_bonus, 1.0)
    
    def _calculate_relationship_quality(
        self,
        relationship_count: int,
        node_count: int
    ) -> float:
        """Calculate relationship quality."""
        if node_count == 0:
            return 0.0
        
        # Ideal relationship density is around 2-3 per node
        ideal_density = 2.5
        actual_density = relationship_count / node_count
        
        # Score based on how close to ideal
        density_score = 1.0 - abs(actual_density - ideal_density) / ideal_density
        
        return max(0, min(density_score, 1.0))
    
    def _calculate_summary_quality(self, stats: Dict[str, Any]) -> float:
        """Calculate summary quality based on document stats."""
        word_count = stats.get("word_count", 0)
        
        if word_count == 0:
            return 0.0
        
        # Longer documents should have more summaries
        # Assume 1 summary per 1000 words is reasonable
        expected_summaries = word_count / 1000
        
        actual_summaries = stats.get("summary_count", 1)
        
        score = min(actual_summaries / max(expected_summaries, 1), 1.0)
        
        return score
    
    def _calculate_citation_coverage(
        self,
        entity_count: int,
        concept_count: int,
        citation_count: int
    ) -> float:
        """Calculate citation coverage."""
        total_items = entity_count + concept_count
        
        if total_items == 0:
            return 0.0
        
        return min(citation_count / total_items, 1.0)
    
    def _calculate_topic_coverage(self, stats: Dict[str, Any]) -> float:
        """Calculate topic coverage."""
        topic_count = stats.get("topic_count", 0)
        word_count = stats.get("word_count", 0)
        
        if word_count == 0:
            return 0.0
        
        # 1 topic per 500 words is reasonable
        expected_topics = word_count / 500
        
        return min(topic_count / max(expected_topics, 1), 1.0)
    
    def _calculate_metadata_completeness(self, stats: Dict[str, Any]) -> float:
        """Calculate metadata completeness."""
        required_fields = ["word_count", "language"]
        optional_fields = ["difficulty_score", "reading_time_minutes", "document_category"]
        
        required_score = sum(1 for f in required_fields if stats.get(f)) / len(required_fields)
        optional_score = sum(1 for f in optional_fields if stats.get(f)) / len(optional_fields)
        
        return required_score * 0.6 + optional_score * 0.4
    
    def _calculate_knowledge_density(
        self,
        entity_count: int,
        concept_count: int,
        relationship_count: int,
        word_count: int
    ) -> float:
        """Calculate knowledge density (knowledge items per word)."""
        if word_count == 0:
            return 0.0
        
        total_items = entity_count + concept_count + relationship_count
        
        # Ideal: 1 item per 50 words
        ideal_ratio = word_count / 50
        actual_ratio = total_items
        
        # Score based on ratio
        if actual_ratio == 0:
            return 0.0
        
        ratio = ideal_ratio / actual_ratio
        
        return min(max(ratio, 0), 1.0)
    
    def _save_quality_score(
        self,
        document_id: int,
        quality: QualityScore,
        entity_count: int,
        concept_count: int,
        relationship_count: int,
        citation_count: int
    ) -> None:
        """Save quality score to database."""
        try:
            # Check if record exists
            existing = self.db.query(KnowledgeQuality).filter(
                KnowledgeQuality.document_id == document_id
            ).first()
            
            if existing:
                # Update
                existing.overall_quality_score = quality.overall
                existing.extraction_completeness = quality.extraction_completeness
                existing.entity_quality = quality.entity_quality
                existing.relationship_quality = quality.relationship_quality
                existing.summary_quality = quality.summary_quality
                existing.citation_coverage = quality.citation_coverage
                existing.topic_coverage = quality.topic_coverage
                existing.metadata_completeness = quality.metadata_completeness
                existing.knowledge_density = quality.knowledge_density
                existing.total_entities = entity_count
                existing.total_concepts = concept_count
                existing.total_relationships = relationship_count
                existing.total_citations = citation_count
            else:
                # Create new
                quality_record = KnowledgeQuality(
                    document_id=document_id,
                    overall_quality_score=quality.overall,
                    extraction_completeness=quality.extraction_completeness,
                    entity_quality=quality.entity_quality,
                    relationship_quality=quality.relationship_quality,
                    summary_quality=quality.summary_quality,
                    citation_coverage=quality.citation_coverage,
                    topic_coverage=quality.topic_coverage,
                    metadata_completeness=quality.metadata_completeness,
                    knowledge_density=quality.knowledge_density,
                    total_entities=entity_count,
                    total_concepts=concept_count,
                    total_relationships=relationship_count,
                    total_citations=citation_count,
                )
                self.db.add(quality_record)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save quality score: {e}")
    
    def get_quality_for_document(self, document_id: int) -> Optional[KnowledgeQuality]:
        """Get quality score for a document."""
        return self.db.query(KnowledgeQuality).filter(
            KnowledgeQuality.document_id == document_id
        ).first()
