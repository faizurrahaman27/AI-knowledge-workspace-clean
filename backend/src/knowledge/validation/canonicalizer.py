"""
Canonicalization Service

Normalizes and standardizes extracted knowledge.
"""

from typing import Dict, Any, List, Optional
import re

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.core.logging import logger


class CanonicalizationService(BaseValidationService):
    """
    Canonicalizes extracted knowledge to standard formats.
    
    Handles:
    - Text normalization
    - Type standardization
    - Format consistency
    - Data type normalization
    """
    
    service_name = "canonicalization"
    estimated_time_ms = 2000
    
    def __init__(self, db: Session):
        """Initialize the canonicalization service."""
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Canonicalization doesn't validate."""
        return ValidationResult(success=True, passed=True)
    
    def canonicalize_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Canonicalize an entity."""
        canonical = entity.copy()
        
        # Normalize name
        canonical["name"] = self._normalize_text(entity.get("name", ""))
        canonical["canonical_name"] = self._normalize_text(entity.get("name", ""))
        
        # Standardize type
        canonical["entity_type"] = self._standardize_entity_type(
            entity.get("entity_type", "other")
        )
        
        # Clean description
        if entity.get("description"):
            canonical["description"] = self._clean_text(entity.get("description"))
        
        return canonical
    
    def canonicalize_concept(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Canonicalize a concept."""
        canonical = concept.copy()
        
        # Normalize name
        canonical["name"] = self._normalize_text(concept.get("name", ""))
        
        # Standardize importance
        canonical["importance"] = self._standardize_importance(
            concept.get("importance", "medium")
        )
        
        # Standardize difficulty
        canonical["difficulty"] = self._standardize_difficulty(
            concept.get("difficulty", "intermediate")
        )
        
        return canonical
    
    def canonicalize_relationship(self, relationship: Dict[str, Any]) -> Dict[str, Any]:
        """Canonicalize a relationship."""
        canonical = relationship.copy()
        
        # Normalize names
        canonical["source_name"] = self._normalize_text(relationship.get("source_name", ""))
        canonical["target_name"] = self._normalize_text(relationship.get("target_name", ""))
        
        # Standardize relationship type
        canonical["relationship_type"] = self._standardize_relationship_type(
            relationship.get("relationship_type", "related_to")
        )
        
        return canonical
    
    def canonicalize_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Canonicalize a question."""
        canonical = question.copy()
        
        # Normalize question text
        canonical["question_text"] = self._normalize_text(question.get("question_text", ""))
        
        # Standardize difficulty
        canonical["difficulty"] = self._standardize_difficulty(
            question.get("difficulty", "intermediate")
        )
        
        # Standardize question type
        canonical["question_type"] = self._standardize_question_type(
            question.get("question_type", "short_answer")
        )
        
        # Clean answer
        if question.get("answer"):
            canonical["answer"] = self._clean_text(question.get("answer"))
        
        return canonical
    
    def canonicalize_flashcard(self, flashcard: Dict[str, Any]) -> Dict[str, Any]:
        """Canonicalize a flashcard."""
        canonical = flashcard.copy()
        
        # Normalize front/back
        canonical["front"] = self._normalize_text(flashcard.get("front", ""))
        canonical["back"] = self._clean_text(flashcard.get("back", ""))
        
        # Standardize difficulty
        canonical["difficulty"] = self._standardize_difficulty(
            flashcard.get("difficulty", "intermediate")
        )
        
        # Clean tags
        if flashcard.get("tags"):
            canonical["tags"] = [self._normalize_text(t) for t in flashcard["tags"]]
        
        return canonical
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        normalized = text.strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _clean_text(self, text: str) -> str:
        """Clean text while preserving structure."""
        if not text:
            return ""
        
        cleaned = text.strip()
        
        # Remove excessive whitespace
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned
    
    def _standardize_entity_type(self, entity_type: str) -> str:
        """Standardize entity type to canonical form."""
        type_mapping = {
            "person": "person",
            "people": "person",
            "individual": "person",
            "organization": "organization",
            "org": "organization",
            "company": "company",
            "business": "company",
            "technology": "technology",
            "tech": "technology",
            "programming_language": "programming_language",
            "programminglanguage": "programming_language",
            "language": "programming_language",
            "framework": "framework",
            "model": "model",
            "ai_model": "model",
            "dataset": "dataset",
            "data": "dataset",
            "library": "library",
            "lib": "library",
            "tool": "tool",
            "website": "website",
            "web": "website",
            "research_paper": "research_paper",
            "paper": "research_paper",
            "book": "book",
            "publication": "book",
            "institution": "institution",
            "institute": "institution",
        }
        
        normalized = entity_type.lower().strip().replace(" ", "_")
        return type_mapping.get(normalized, entity_type)
    
    def _standardize_importance(self, importance: str) -> str:
        """Standardize importance level."""
        mapping = {
            "high": "high",
            "important": "high",
            "medium": "medium",
            "moderate": "medium",
            "avg": "medium",
            "low": "low",
            "minor": "low",
        }
        
        normalized = importance.lower().strip()
        return mapping.get(normalized, "medium")
    
    def _standardize_difficulty(self, difficulty: str) -> str:
        """Standardize difficulty level."""
        mapping = {
            "beginner": "beginner",
            "basic": "beginner",
            "easy": "beginner",
            "intermediate": "intermediate",
            "medium": "intermediate",
            "moderate": "intermediate",
            "advanced": "advanced",
            "hard": "advanced",
            "expert": "advanced",
        }
        
        normalized = difficulty.lower().strip()
        return mapping.get(normalized, "intermediate")
    
    def _standardize_relationship_type(self, rel_type: str) -> str:
        """Standardize relationship type."""
        mapping = {
            "uses": "uses",
            "use": "uses",
            "using": "uses",
            "implements": "implements",
            "implement": "implements",
            "depends_on": "depends_on",
            "depends": "depends_on",
            "depends_on": "depends_on",
            "requires": "requires",
            "require": "requires",
            "enables": "enables",
            "enable": "enables",
            "extends": "extends",
            "extend": "extends",
            "composed_of": "composed_of",
            "composes": "composed_of",
            "part_of": "part_of",
            "related_to": "related_to",
            "related": "related_to",
            "defined_in": "defined_in",
            "introduced_by": "introduced_by",
            "authored_by": "authored_by",
            "published_in": "published_in",
        }
        
        normalized = rel_type.lower().strip().replace(" ", "_")
        return mapping.get(normalized, rel_type)
    
    def _standardize_question_type(self, q_type: str) -> str:
        """Standardize question type."""
        mapping = {
            "multiple_choice": "multiple_choice",
            "mcq": "multiple_choice",
            "mc": "multiple_choice",
            "short_answer": "short_answer",
            "short": "short_answer",
            "conceptual": "conceptual",
            "concept": "conceptual",
            "analytical": "analytical",
            "analysis": "analytical",
            "scenario_based": "scenario_based",
            "scenario": "scenario_based",
            "coding": "coding",
            "code": "coding",
        }
        
        normalized = q_type.lower().strip().replace(" ", "_")
        return mapping.get(normalized, q_type)
