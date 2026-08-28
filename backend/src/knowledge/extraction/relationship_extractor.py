"""
Relationship Extraction Service

Extracts relationships between entities and concepts.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.knowledge.models import RelationshipType
from src.core.logging import logger


class RelationshipExtractionService(BaseExtractionService):
    """
    Service for extracting relationships between entities and concepts.
    
    Relationships form the basis for knowledge graph generation.
    
    Example relationships:
    - Transformer USES Attention
    - PyTorch IMPLEMENTS Neural Networks
    - Backpropagation REQUIRES Calculus
    """
    
    service_name = "relationship_extraction"
    estimated_time_ms = 20000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Extract relationships from document text.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of extracted relationships with metadata
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.2, "Identifying relationships...")
        
        process_text = text[:6000]
        
        prompt = f"""Extract meaningful relationships between concepts, entities, and technologies from the text.
For each relationship, identify:
1. source_name: Name of the source entity/concept
2. source_type: Type of source ('entity' or 'concept')
3. relationship_type: Type of relationship (uses, implements, depends_on, requires, enables, extends, composed_of, part_of, related_to, defined_in, introduced_by, authored_by, published_in)
4. target_name: Name of the target entity/concept
5. target_type: Type of target ('entity' or 'concept')
6. description: Brief description of the relationship
7. evidence: Text evidence from the document supporting this relationship

Return as JSON array.

Text:
{process_text}

Example output:
[
  {{
    "source_name": "Transformer",
    "source_type": "concept",
    "relationship_type": "uses",
    "target_name": "Attention",
    "target_type": "concept",
    "description": "Transformers use self-attention mechanisms",
    "evidence": "The Transformer architecture uses self-attention instead of recurrence"
  }}
]"""
        
        system_prompt = """You are an expert at identifying relationships between concepts.
Extract meaningful, well-supported relationships.
Return valid JSON arrays only."""
        
        try:
            context.emit_progress(self.service_name, 0.6, "Parsing relationships...")
            response = self._get_llm_response(prompt, system_prompt)
            
            relationships = json.loads(response)
            
            validated_relationships = []
            for rel in relationships:
                if self._validate_relationship(rel):
                    validated_relationships.append({
                        "source_type": rel.get("source_type", "concept"),
                        "source_name": rel.get("source_name", ""),
                        "relationship_type": rel.get("relationship_type", "related_to"),
                        "target_type": rel.get("target_type", "concept"),
                        "target_name": rel.get("target_name", ""),
                        "description": rel.get("description"),
                        "evidence": rel.get("evidence"),
                        "confidence_score": 0.7,
                        "is_inferred": False,
                    })
            
            context.emit_progress(
                self.service_name, 1.0,
                f"Extracted {len(validated_relationships)} relationships"
            )
            
            return validated_relationships
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse relationship extraction response: {e}")
            return []
        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")
            return []
    
    def _validate_relationship(self, rel: Dict) -> bool:
        """Validate an extracted relationship."""
        if not rel.get("source_name") or not rel.get("target_name"):
            return False
        if not rel.get("relationship_type"):
            return False
        # Normalize relationship type
        rel_type = rel.get("relationship_type", "").lower().replace(" ", "_")
        valid_types = [r.value for r in RelationshipType]
        if rel_type not in valid_types:
            rel["relationship_type"] = "related_to"
        return True
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at identifying relationships between technical concepts.
Extract meaningful, well-evidenced relationships.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock relationship response for testing."""
        return """[
  {
    "source_name": "Deep Learning",
    "source_type": "concept",
    "relationship_type": "uses",
    "target_name": "Neural Networks",
    "target_type": "concept",
    "description": "Deep learning uses neural network architectures",
    "evidence": "Deep learning is a subset of machine learning using neural networks"
  }
]"""
