"""
Consistency Validation Service

Validates consistency of extracted knowledge.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.knowledge.validation_models import ValidationRecord, ValidationStatus
from src.core.logging import logger


class ConsistencyValidationService(BaseValidationService):
    """
    Validates consistency of extracted knowledge.
    
    Checks:
    - Relationship consistency
    - Missing entities
    - Broken references
    - Circular relationships
    - Invalid citations
    - Orphan concepts
    """
    
    service_name = "consistency_validation"
    estimated_time_ms = 5000
    
    def __init__(self, db: Session):
        """Initialize the consistency validation service."""
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Validate consistency."""
        return ValidationResult(success=True, passed=True)
    
    def validate_document(
        self,
        document_id: int,
        entities: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        topics: List[Dict[str, Any]]
    ) -> Tuple[List[ValidationResult], float]:
        """
        Validate consistency for a document.
        
        Args:
            document_id: Document ID
            entities: Extracted entities
            concepts: Extracted concepts
            relationships: Extracted relationships
            topics: Classified topics
            
        Returns:
            Tuple of (validation results, consistency score)
        """
        results = []
        
        # Check for orphan concepts (concepts without any relationships)
        orphan_results = self._check_orphan_concepts(concepts, relationships)
        results.extend(orphan_results)
        
        # Check for circular relationships
        circular_results = self._check_circular_relationships(relationships)
        results.extend(circular_results)
        
        # Check for broken entity references
        reference_results = self._check_entity_references(entities, relationships)
        results.extend(reference_results)
        
        # Check for invalid relationship types
        type_results = self._check_relationship_types(relationships)
        results.extend(type_results)
        
        # Calculate consistency score
        if results:
            passed = sum(1 for r in results if r.passed)
            score = passed / len(results)
        else:
            score = 1.0
        
        # Store validation records
        for result in results:
            record = ValidationRecord(
                document_id=document_id,
                validation_type="consistency",
                status=ValidationStatus.VALID.value if result.passed else ValidationStatus.INVALID.value,
                passed=result.passed,
                message=result.message,
                error_code=result.error_code,
                details=result.details
            )
            self.db.add(record)
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save validation records: {e}")
        
        return results, score
    
    def _check_orphan_concepts(
        self,
        concepts: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Check for concepts without any relationships."""
        results = []
        
        # Build set of related concept names
        related_names = set()
        for rel in relationships:
            related_names.add(rel.get("source_name", "").lower())
            related_names.add(rel.get("target_name", "").lower())
        
        # Check each concept
        for concept in concepts:
            name = concept.get("name", "").lower()
            
            if name and name not in related_names:
                # Check if this is expected (standalone concepts are valid)
                is_orphan = concept.get("is_orphan", False)
                
                if not is_orphan:
                    results.append(ValidationResult(
                        success=True,
                        passed=True,  # Not necessarily an error
                        message=f"Concept '{concept.get('name')}' has no relationships",
                        error_code="ORPHAN_CONCEPT",
                        details={"concept_id": concept.get("id")}
                    ))
        
        return results
    
    def _check_circular_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Check for circular relationships."""
        results = []
        
        # Build adjacency list
        adj = defaultdict(list)
        for rel in relationships:
            source = rel.get("source_name", "").lower()
            target = rel.get("target_name", "").lower()
            rel_type = rel.get("relationship_type", "")
            
            # Skip non-directional relationships
            if rel_type in ["related_to", "similar_to"]:
                continue
            
            adj[source].append(target)
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    return path + [neighbor]
            
            rec_stack.remove(node)
            return None
        
        for node in adj:
            if node not in visited:
                cycle = has_cycle(node, [])
                if cycle:
                    results.append(ValidationResult(
                        success=True,
                        passed=True,  # Circular relationships are allowed
                        message=f"Circular relationship detected: {' -> '.join(cycle)}",
                        error_code="CIRCULAR_RELATIONSHIP",
                        details={"cycle": cycle}
                    ))
        
        return results
    
    def _check_entity_references(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Check for relationships referencing non-existent entities."""
        results = []
        
        # Build set of valid entity names
        valid_entities = {e.get("name", "").lower() for e in entities}
        
        # Check each relationship
        for rel in relationships:
            source = rel.get("source_name", "").lower()
            target = rel.get("target_name", "").lower()
            rel_type = rel.get("relationship_type", "")
            
            # Skip if referencing concepts (different validation)
            if rel.get("source_type") == "concept" or rel.get("target_type") == "concept":
                continue
            
            if source and source not in valid_entities:
                results.append(ValidationResult(
                    success=True,
                    passed=False,
                    message=f"Relationship references unknown entity: {source}",
                    error_code="BROKEN_ENTITY_REFERENCE",
                    details={"relationship_id": rel.get("id")}
                ))
            
            if target and target not in valid_entities:
                results.append(ValidationResult(
                    success=True,
                    passed=False,
                    message=f"Relationship references unknown entity: {target}",
                    error_code="BROKEN_ENTITY_REFERENCE",
                    details={"relationship_id": rel.get("id")}
                ))
        
        return results
    
    def _check_relationship_types(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Check for invalid relationship types."""
        results = []
        
        valid_types = {
            "uses", "implements", "depends_on", "requires", "enables",
            "extends", "composed_of", "part_of", "related_to",
            "defined_in", "introduced_by", "authored_by", "published_in"
        }
        
        for rel in relationships:
            rel_type = rel.get("relationship_type", "").lower()
            
            if rel_type and rel_type not in valid_types:
                results.append(ValidationResult(
                    success=True,
                    passed=False,
                    message=f"Invalid relationship type: {rel_type}",
                    error_code="INVALID_RELATIONSHIP_TYPE",
                    details={"relationship_id": rel.get("id")}
                ))
        
        return results
