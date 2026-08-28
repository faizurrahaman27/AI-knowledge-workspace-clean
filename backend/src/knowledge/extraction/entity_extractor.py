"""
Entity Extraction Service

Extracts named entities from documents using LLM.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.knowledge.models import EntityType
from src.core.logging import logger


class EntityExtractionService(BaseExtractionService):
    """
    Service for extracting named entities from documents.
    
    Extracts entities of types:
    - Person
    - Organization
    - Company
    - Technology
    - Programming Language
    - Framework
    - Model
    - Dataset
    - Library
    - Tool
    - Website
    - Research Paper
    - Book
    - Institution
    """
    
    service_name = "entity_extraction"
    estimated_time_ms = 15000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Extract named entities from document text.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of extracted entities with metadata
        """
        text = context.text
        
        # Split into chunks for large documents
        chunk_size = 4000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        all_entities = []
        
        for i, chunk in enumerate(chunks):
            context.emit_progress(
                self.service_name, 
                0.2 + (0.6 * i / len(chunks)),
                f"Extracting entities from chunk {i+1}/{len(chunks)}..."
            )
            
            entities = self._extract_from_chunk(chunk)
            all_entities.extend(entities)
        
        # Deduplicate entities by name and type
        context.emit_progress(self.service_name, 0.9, "Deduplicating entities...")
        unique_entities = self._deduplicate_entities(all_entities)
        
        context.emit_progress(self.service_name, 1.0, f"Extracted {len(unique_entities)} entities")
        
        return unique_entities
    
    def _extract_from_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        """Extract entities from a single chunk of text."""
        prompt = f"""Extract all named entities from the following text. For each entity, identify:
1. name: The entity name
2. type: The entity type (one of: person, organization, company, technology, programming_language, framework, model, dataset, library, tool, website, research_paper, book, institution, product, event, location, other)
3. description: Brief description of the entity (1-2 sentences)
4. confidence: Confidence score (0.0-1.0) for the entity extraction

Return the results as a JSON array of objects.

Text:
{chunk}

Example output format:
[
  {{"name": "John Smith", "type": "person", "description": "A software engineer", "confidence": 0.95}},
  {{"name": "Google", "type": "company", "description": "Technology company", "confidence": 0.98}}
]"""
        
        system_prompt = """You are an expert NER (Named Entity Recognition) system.
Extract all meaningful named entities from the text. Be thorough but accurate.
Return valid JSON only."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            
            # Parse JSON response
            entities = json.loads(response)
            
            # Validate and normalize entities
            validated_entities = []
            for entity in entities:
                if self._validate_entity(entity):
                    validated_entities.append({
                        "name": entity.get("name", ""),
                        "entity_type": entity.get("type", "other"),
                        "canonical_name": entity.get("canonical_name"),
                        "description": entity.get("description"),
                        "confidence_score": float(entity.get("confidence", 0.7)),
                    })
            
            return validated_entities
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entity extraction response: {e}")
            return []
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    def _validate_entity(self, entity: Dict) -> bool:
        """Validate an extracted entity."""
        if not entity.get("name"):
            return False
        if len(entity.get("name", "")) < 2:
            return False
        if entity.get("type") not in [e.value for e in EntityType]:
            # Allow 'other' for unknown types
            entity["type"] = "other"
        return True
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on name and type."""
        seen = {}
        unique = []
        
        for entity in entities:
            key = (entity["name"].lower().strip(), entity["entity_type"])
            
            if key not in seen:
                seen[key] = entity
                entity["mentions"] = 1
                entity["first_mention"] = None
                unique.append(entity)
            else:
                # Increment mention count
                seen[key]["mentions"] = seen[key].get("mentions", 1) + 1
                # Update confidence with higher value
                if entity.get("confidence_score", 0) > seen[key].get("confidence_score", 0):
                    seen[key]["confidence_score"] = entity["confidence_score"]
        
        # Sort by confidence and mentions
        unique.sort(
            key=lambda e: (e.get("confidence_score", 0), e.get("mentions", 0)),
            reverse=True
        )
        
        return unique[:100]  # Limit to top 100 entities
    
    def _get_system_prompt(self) -> str:
        return """You are an expert Named Entity Recognition system.
Extract all meaningful entities with high accuracy.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock entity response for testing."""
        return """[
  {"name": "Python", "type": "programming_language", "description": "High-level programming language", "confidence": 0.95},
  {"name": "Machine Learning", "type": "technology", "description": "Field of AI", "confidence": 0.92},
  {"name": "TensorFlow", "type": "framework", "description": "ML framework by Google", "confidence": 0.94}
]"""
