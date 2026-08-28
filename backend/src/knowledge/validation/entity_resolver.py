"""
Entity Resolution Service

Resolves duplicate entities using normalization and canonicalization.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.knowledge.validation_models import CanonicalEntity
from src.core.logging import logger


class EntityResolutionService(BaseValidationService):
    """
    Resolves duplicate entities through normalization and canonicalization.
    
    Handles variations like:
    - "OpenAI", "Open AI", "Open-AI"
    - "PyTorch", "torch"
    - "TensorFlow 2", "TF2", "TensorFlow"
    """
    
    service_name = "entity_resolution"
    estimated_time_ms = 5000
    
    # Normalization rules
    NORMALIZATION_RULES = [
        # Remove extra spaces
        (r'\s+', ' '),
        # Remove hyphens
        (r'[-_]', ''),
        # Remove common suffixes
        (r'\s+(Inc|LLC|Corp|Ltd|Co)\.?$', ''),
        # Remove version numbers
        (r'\s+v?\d+\.?\d*$', ''),
        # Remove common prefixes
        (r'^(The)\s+', ''),
    ]
    
    # Similarity threshold for fuzzy matching
    SIMILARITY_THRESHOLD = 0.85
    
    def __init__(self, db: Session):
        """
        Initialize the entity resolution service.
        
        Args:
            db: Database session
        """
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Entity resolution doesn't validate."""
        return ValidationResult(success=True, passed=True)
    
    def resolve_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None
    ) -> Tuple[int, bool]:
        """
        Resolve an entity to its canonical form.
        
        Args:
            name: Entity name
            entity_type: Type of entity
            description: Optional description
            
        Returns:
            Tuple of (canonical_entity_id, was_merged)
        """
        normalized_name = self._normalize(name)
        
        # Check if canonical entity exists
        canonical = self._find_canonical(normalized_name, entity_type)
        
        if canonical:
            # Update statistics
            canonical.occurrence_count += 1
            self.db.commit()
            
            # Add alias if different
            if normalized_name != canonical.canonical_name.lower():
                aliases = canonical.aliases or []
                if name not in aliases:
                    aliases.append(name)
                    canonical.aliases = aliases
            
            return canonical.id, False
        
        # Create new canonical entity
        canonical = CanonicalEntity(
            canonical_name=normalized_name,
            entity_type=entity_type,
            aliases=[name] if name != normalized_name else [],
            canonical_description=description,
            occurrence_count=1,
            document_count=1,
        )
        
        self.db.add(canonical)
        self.db.commit()
        self.db.refresh(canonical)
        
        return canonical.id, True
    
    def _normalize(self, name: str) -> str:
        """Normalize entity name for comparison."""
        if not name:
            return ""
        
        normalized = name.strip().lower()
        
        # Apply normalization rules
        for pattern, replacement in self.NORMALIZATION_RULES:
            if pattern:
                normalized = re.sub(pattern, replacement or '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _find_canonical(
        self,
        normalized_name: str,
        entity_type: str
    ) -> Optional[CanonicalEntity]:
        """Find existing canonical entity."""
        # Exact match
        canonical = self.db.query(CanonicalEntity).filter(
            CanonicalEntity.canonical_name == normalized_name,
            CanonicalEntity.entity_type == entity_type
        ).first()
        
        if canonical:
            return canonical
        
        # Fuzzy match
        all_canonical = self.db.query(CanonicalEntity).filter(
            CanonicalEntity.entity_type == entity_type
        ).all()
        
        for candidate in all_canonical:
            # Check against canonical name
            similarity = self._calculate_similarity(normalized_name, candidate.canonical_name.lower())
            if similarity >= self.SIMILARITY_THRESHOLD:
                return candidate
            
            # Check against aliases
            for alias in candidate.aliases or []:
                alias_similarity = self._calculate_similarity(normalized_name, alias.lower())
                if alias_similarity >= self.SIMILARITY_THRESHOLD:
                    return candidate
        
        return None
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def merge_entities(
        self,
        source_id: int,
        target_id: int
    ) -> bool:
        """
        Merge two entities, with source being merged into target.
        
        Args:
            source_id: Entity to merge from
            target_id: Entity to merge into
            
        Returns:
            True if successful
        """
        source = self.db.query(CanonicalEntity).filter(
            CanonicalEntity.id == source_id
        ).first()
        
        target = self.db.query(CanonicalEntity).filter(
            CanonicalEntity.id == target_id
        ).first()
        
        if not source or not target:
            return False
        
        # Merge aliases
        merged_aliases = list(set((source.aliases or []) + (target.aliases or [])))
        target.aliases = merged_aliases
        
        # Update statistics
        target.occurrence_count += source.occurrence_count
        target.document_count = max(target.document_count, source.document_count)
        
        # Store merged entity ID
        merged_ids = target.merged_entity_ids or []
        merged_ids.append(source_id)
        target.merged_entity_ids = merged_ids
        
        # Delete source
        self.db.delete(source)
        self.db.commit()
        
        logger.info(f"Merged entity {source_id} into {target_id}")
        
        return True
    
    def get_canonical_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[CanonicalEntity]:
        """Get canonical entities, optionally filtered by type."""
        query = self.db.query(CanonicalEntity)
        
        if entity_type:
            query = query.filter(CanonicalEntity.entity_type == entity_type)
        
        return query.order_by(
            CanonicalEntity.occurrence_count.desc()
        ).limit(limit).all()
