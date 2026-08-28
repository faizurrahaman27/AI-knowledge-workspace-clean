"""
Semantic Tagging Service

Generates semantic tags for documents.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.knowledge.models import TagCategory
from src.core.logging import logger


class SemanticTaggingService(BaseExtractionService):
    """
    Service for generating semantic tags for documents.
    
    Generates tags in categories:
    - Skills
    - Technologies
    - Industries
    - Academic Domains
    - Programming Languages
    - Libraries
    - Frameworks
    - Research Areas
    - Career Domains
    """
    
    service_name = "semantic_tagging"
    estimated_time_ms = 10000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Generate semantic tags for document.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of semantic tags with categories
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.3, "Generating semantic tags...")
        
        prompt = f"""Analyze the following text and generate semantic tags.
For each tag include:
1. tag: The tag name
2. tag_category: Category (skill, technology, industry, academic_domain, programming_language, library, framework, research_area, career_domain)
3. context: How/why this tag applies
4. relevance_score: Relevance score (0.0-1.0)

Return as JSON array.

Text:
{text[:4000]}

Example output:
[
  {{"tag": "Python", "tag_category": "programming_language", "context": "Primary language used", "relevance_score": 0.9}},
  {{"tag": "Machine Learning", "tag_category": "skill", "context": "Core skill demonstrated", "relevance_score": 0.95}}
]"""
        
        system_prompt = """You are an expert at generating semantic tags.
Generate relevant, specific tags across multiple categories.
Return valid JSON arrays only."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            tags = json.loads(response)
            
            validated_tags = []
            for tag in tags:
                if self._validate_tag(tag):
                    validated_tags.append({
                        "tag": tag.get("tag", ""),
                        "tag_category": tag.get("tag_category", TagCategory.SKILL.value),
                        "context": tag.get("context"),
                        "relevance_score": float(tag.get("relevance_score", 0.7)),
                    })
            
            context.emit_progress(
                self.service_name, 1.0,
                f"Generated {len(validated_tags)} tags"
            )
            
            return validated_tags
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse semantic tagging response: {e}")
            return []
        except Exception as e:
            logger.error(f"Semantic tagging failed: {e}")
            return []
    
    def _validate_tag(self, tag: Dict) -> bool:
        """Validate a generated tag."""
        if not tag.get("tag"):
            return False
        if len(tag.get("tag", "")) < 2:
            return False
        return True
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at generating semantic tags.
Generate relevant, specific tags.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock tag response for testing."""
        return """[
  {"tag": "Machine Learning", "tag_category": "skill", "context": "Core topic", "relevance_score": 0.95},
  {"tag": "Python", "tag_category": "programming_language", "context": "Used for implementation", "relevance_score": 0.9},
  {"tag": "TensorFlow", "tag_category": "library", "context": "ML framework used", "relevance_score": 0.85}
]"""
