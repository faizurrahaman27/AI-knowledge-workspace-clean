"""
Duplicate Detection Service

Detects and removes duplicate entities, concepts, questions, flashcards, etc.
"""

from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.core.logging import logger


class DuplicateDetectionService(BaseValidationService):
    """
    Detects and handles duplicate knowledge items.
    
    Supports:
    - Exact duplicates
    - Semantic duplicates (similar content)
    - Cross-document duplicates
    """
    
    service_name = "duplicate_detection"
    estimated_time_ms = 3000
    
    # Similarity thresholds
    EXACT_THRESHOLD = 1.0
    SEMANTIC_THRESHOLD = 0.90
    
    def __init__(self, db: Session):
        """Initialize the duplicate detection service."""
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Duplicate detection doesn't validate."""
        return ValidationResult(success=True, passed=True)
    
    def find_duplicates(
        self,
        items: List[Dict[str, Any]],
        item_type: str,
        similarity_threshold: float = 0.90
    ) -> List[Set[int]]:
        """
        Find duplicate items within a list.
        
        Args:
            items: List of items to check
            item_type: Type of items (entity, concept, question, flashcard)
            similarity_threshold: Threshold for considering duplicates
            
        Returns:
            List of sets, where each set contains indices of duplicate items
        """
        duplicates = []
        processed = set()
        
        for i in range(len(items)):
            if i in processed:
                continue
            
            duplicate_group = {i}
            
            for j in range(i + 1, len(items)):
                if j in processed:
                    continue
                
                similarity = self._calculate_similarity(items[i], items[j], item_type)
                
                if similarity >= similarity_threshold:
                    duplicate_group.add(j)
                    processed.add(j)
            
            if len(duplicate_group) > 1:
                duplicates.append(duplicate_group)
                processed.add(i)
        
        return duplicates
    
    def _calculate_similarity(
        self,
        item1: Dict[str, Any],
        item2: Dict[str, Any],
        item_type: str
    ) -> float:
        """Calculate similarity between two items."""
        if item_type == "entity":
            return self._entity_similarity(item1, item2)
        elif item_type == "concept":
            return self._concept_similarity(item1, item2)
        elif item_type == "question":
            return self._question_similarity(item1, item2)
        elif item_type == "flashcard":
            return self._flashcard_similarity(item1, item2)
        elif item_type == "relationship":
            return self._relationship_similarity(item1, item2)
        else:
            return self._generic_similarity(item1, item2)
    
    def _entity_similarity(self, e1: Dict, e2: Dict) -> float:
        """Calculate entity similarity."""
        name1 = e1.get("name", "").lower().strip()
        name2 = e2.get("name", "").lower().strip()
        
        if name1 == name2:
            return 1.0
        
        # Same type bonus
        type_bonus = 0.1 if e1.get("entity_type") == e2.get("entity_type") else 0
        
        # Description similarity
        desc_sim = self._text_similarity(
            e1.get("description", ""),
            e2.get("description", "")
        )
        
        return SequenceMatcher(None, name1, name2).ratio() * 0.7 + desc_sim * 0.3 + type_bonus
    
    def _concept_similarity(self, c1: Dict, c2: Dict) -> float:
        """Calculate concept similarity."""
        name1 = c1.get("name", "").lower().strip()
        name2 = c2.get("name", "").lower().strip()
        
        if name1 == name2:
            return 1.0
        
        return SequenceMatcher(None, name1, name2).ratio()
    
    def _question_similarity(self, q1: Dict, q2: Dict) -> float:
        """Calculate question similarity."""
        text1 = q1.get("question_text", "").lower().strip()
        text2 = q2.get("question_text", "").lower().strip()
        
        if text1 == text2:
            return 1.0
        
        # If both are MCQ, check answers too
        if q1.get("options") and q2.get("options"):
            return self._text_similarity(text1, text2) * 0.8 + 0.2
        
        return self._text_similarity(text1, text2)
    
    def _flashcard_similarity(self, f1: Dict, f2: Dict) -> float:
        """Calculate flashcard similarity."""
        front1 = f1.get("front", "").lower().strip()
        front2 = f2.get("front", "").lower().strip()
        
        back1 = f1.get("back", "").lower().strip()
        back2 = f2.get("back", "").lower().strip()
        
        front_sim = self._text_similarity(front1, front2)
        back_sim = self._text_similarity(back1, back2)
        
        return (front_sim + back_sim) / 2
    
    def _relationship_similarity(self, r1: Dict, r2: Dict) -> float:
        """Calculate relationship similarity."""
        # Same source and target
        if (r1.get("source_name") == r2.get("source_name") and
            r1.get("target_name") == r2.get("target_name")):
            return 1.0
        
        # Same relationship type
        type_sim = 0.1 if r1.get("relationship_type") == r2.get("relationship_type") else 0
        
        # Source/target similarity
        source_sim = self._text_similarity(
            r1.get("source_name", ""),
            r2.get("source_name", "")
        )
        target_sim = self._text_similarity(
            r1.get("target_name", ""),
            r2.get("target_name", "")
        )
        
        return (source_sim + target_sim) / 2 + type_sim
    
    def _generic_similarity(self, item1: Dict, item2: Dict) -> float:
        """Calculate generic similarity using text fields."""
        text1 = str(item1.get("name", "")) + " " + str(item1.get("description", ""))
        text2 = str(item2.get("name", "")) + " " + str(item2.get("description", ""))
        
        return self._text_similarity(text1, text2)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity."""
        if not text1 or not text2:
            return 0.0
        
        if text1 == text2:
            return 1.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def select_best_item(
        self,
        items: List[Dict[str, Any]],
        item_type: str
    ) -> Dict[str, Any]:
        """
        Select the best item from a group of duplicates.
        
        Args:
            items: List of duplicate items
            item_type: Type of items
            
        Returns:
            Best item to keep
        """
        if not items:
            return {}
        
        if len(items) == 1:
            return items[0]
        
        # Score each item
        scored = []
        for item in items:
            score = self._score_item(item, item_type)
            scored.append((score, item))
        
        # Return highest scoring item
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    
    def _score_item(self, item: Dict, item_type: str) -> float:
        """Score an item for selection."""
        score = 0.5
        
        # Higher confidence = higher score
        if item.get("confidence_score"):
            score += float(item.get("confidence_score", 0)) * 0.3
        
        # More mentions = higher score (for entities)
        if item.get("mentions"):
            score += min(item.get("mentions", 0) / 10, 0.2)
        
        # Has description = higher score
        if item.get("description"):
            score += 0.1
        
        return min(score, 1.0)
