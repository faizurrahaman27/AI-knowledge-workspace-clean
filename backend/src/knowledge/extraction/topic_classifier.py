"""
Topic Classification Service

Classifies documents into topics and categories.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.core.logging import logger


class TopicClassificationService(BaseExtractionService):
    """
    Service for classifying documents into topics and categories.
    
    Classifies:
    - Primary topic
    - Secondary topics
    - Categories
    - Hierarchies
    - Prerequisites
    """
    
    service_name = "topic_classification"
    estimated_time_ms = 12000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Classify document into topics.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of topics with classification information
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.3, "Classifying topics...")
        
        prompt = f"""Analyze the following text and classify it into topics.
For each topic identify:
1. topic_name: Name of the topic
2. topic_type: Type (primary, secondary, tertiary)
3. category: Broad category
4. subcategory: Sub-category if applicable
5. hierarchy_path: Array representing topic hierarchy
6. prerequisite_topics: Topics needed before this one
7. related_topics: Related topic names
8. confidence_score: Confidence in the classification (0.0-1.0)
9. importance_score: How central this topic is to the document (0.0-1.0)

Return as JSON array.

Text:
{text[:5000]}

Example output:
[
  {{
    "topic_name": "Machine Learning",
    "topic_type": "primary",
    "category": "Computer Science",
    "subcategory": "Artificial Intelligence",
    "hierarchy_path": ["Computer Science", "Artificial Intelligence", "Machine Learning"],
    "prerequisite_topics": ["Statistics", "Linear Algebra"],
    "related_topics": ["Deep Learning", "Data Science"],
    "confidence_score": 0.95,
    "importance_score": 0.9
  }}
]"""
        
        system_prompt = """You are an expert at topic classification.
Accurately identify and classify topics at appropriate granularity.
Return valid JSON arrays only."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            topics = json.loads(response)
            
            validated_topics = []
            for topic in topics:
                if self._validate_topic(topic):
                    validated_topics.append({
                        "topic_name": topic.get("topic_name", ""),
                        "topic_type": topic.get("topic_type", "secondary"),
                        "category": topic.get("category"),
                        "subcategory": topic.get("subcategory"),
                        "hierarchy_path": topic.get("hierarchy_path", []),
                        "prerequisite_topics": topic.get("prerequisite_topics", []),
                        "related_topics": topic.get("related_topics", []),
                        "confidence_score": float(topic.get("confidence_score", 0.7)),
                        "importance_score": float(topic.get("importance_score", 0.5)),
                    })
            
            context.emit_progress(
                self.service_name, 1.0,
                f"Identified {len(validated_topics)} topics"
            )
            
            return validated_topics
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse topic classification response: {e}")
            return []
        except Exception as e:
            logger.error(f"Topic classification failed: {e}")
            return []
    
    def _validate_topic(self, topic: Dict) -> bool:
        """Validate a classified topic."""
        if not topic.get("topic_name"):
            return False
        if len(topic.get("topic_name", "")) < 2:
            return False
        return True
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at topic classification.
Accurately identify and classify topics.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock topic response for testing."""
        return """[
  {
    "topic_name": "Neural Networks",
    "topic_type": "primary",
    "category": "Computer Science",
    "subcategory": "Artificial Intelligence",
    "hierarchy_path": ["Computer Science", "Artificial Intelligence", "Neural Networks"],
    "prerequisite_topics": ["Linear Algebra", "Python"],
    "related_topics": ["Deep Learning", "Machine Learning"],
    "confidence_score": 0.92,
    "importance_score": 0.95
  }
]"""
