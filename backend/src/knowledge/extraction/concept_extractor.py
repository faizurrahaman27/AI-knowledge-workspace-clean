"""
Concept Extraction Service

Extracts abstract concepts from documents independently of entities.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.core.logging import logger


class ConceptExtractionService(BaseExtractionService):
    """
    Service for extracting abstract concepts from documents.
    
    Concepts are ideas, techniques, methods, principles, etc.
    that exist independently of named entities.
    
    Examples:
    - Gradient Descent
    - Backpropagation
    - Attention Mechanism
    - Transfer Learning
    - Cross-Validation
    """
    
    service_name = "concept_extraction"
    estimated_time_ms = 15000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Extract concepts from document text.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of extracted concepts with metadata
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.2, "Identifying concepts...")
        
        # For concepts, we process the full text but limit for LLM
        process_text = text[:8000]
        
        prompt = f"""Extract all important concepts, ideas, techniques, methods, and principles from the following text.
For each concept, identify:
1. name: The concept name (prefer common/canonical names)
2. description: Brief explanation of the concept (2-3 sentences)
3. importance: How important is this concept (high, medium, low)
4. difficulty: Difficulty level (beginner, intermediate, advanced)
5. related_concepts: List of related concept names
6. usage_examples: List of how this concept is used/applied

Return the results as a JSON array of objects.

Text:
{process_text}

Example output:
[
  {{
    "name": "Gradient Descent",
    "description": "An optimization algorithm used to minimize neural network loss",
    "importance": "high",
    "difficulty": "intermediate",
    "related_concepts": ["Backpropagation", "Learning Rate", "Loss Function"],
    "usage_examples": ["Training neural networks", "Optimizing model parameters"]
  }}
]"""
        
        system_prompt = """You are an expert at identifying and explaining technical concepts.
Focus on extracting abstract ideas, techniques, methods, and principles.
Return valid JSON only."""
        
        try:
            context.emit_progress(self.service_name, 0.6, "Parsing concepts...")
            response = self._get_llm_response(prompt, system_prompt)
            
            concepts = json.loads(response)
            
            # Validate and normalize concepts
            validated_concepts = []
            for concept in concepts:
                if self._validate_concept(concept):
                    validated_concepts.append({
                        "name": concept.get("name", ""),
                        "description": concept.get("description"),
                        "importance": concept.get("importance", "medium"),
                        "difficulty": concept.get("difficulty", "intermediate"),
                        "related_concepts": concept.get("related_concepts", []),
                        "confidence_score": 0.7,
                    })
            
            context.emit_progress(
                self.service_name, 1.0, 
                f"Extracted {len(validated_concepts)} concepts"
            )
            
            return validated_concepts
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse concept extraction response: {e}")
            return []
        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return []
    
    def _validate_concept(self, concept: Dict) -> bool:
        """Validate an extracted concept."""
        if not concept.get("name"):
            return False
        if len(concept.get("name", "")) < 3:
            return False
        return True
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at identifying and explaining technical concepts.
Extract all meaningful concepts with accurate descriptions.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock concept response for testing."""
        return """[
  {
    "name": "Neural Networks",
    "description": "Computing systems inspired by biological neural networks that learn from examples",
    "importance": "high",
    "difficulty": "intermediate",
    "related_concepts": ["Deep Learning", "Backpropagation", "Activation Functions"],
    "usage_examples": ["Image recognition", "Natural language processing"]
  },
  {
    "name": "Transfer Learning",
    "description": "Machine learning technique where knowledge from one task is applied to another",
    "importance": "high",
    "difficulty": "advanced",
    "related_concepts": ["Fine-tuning", "Pre-trained Models"],
    "usage_examples": ["Domain adaptation", "Model compression"]
  }
]"""
