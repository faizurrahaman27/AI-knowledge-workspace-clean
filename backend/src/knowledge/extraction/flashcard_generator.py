"""
Flashcard Generation Service

Generates flashcards for spaced repetition learning.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.knowledge.models import DifficultyLevel
from src.core.logging import logger


class FlashcardGenerationService(BaseExtractionService):
    """
    Service for generating flashcards from document content.
    
    Flashcards are designed for spaced repetition learning.
    Each flashcard has:
    - Front (question/prompt)
    - Back (answer)
    - Topic
    - Difficulty
    - Tags
    """
    
    service_name = "flashcard_generation"
    estimated_time_ms = 20000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Generate flashcards from document text.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of generated flashcards
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.2, "Generating flashcards...")
        
        prompt = f"""Generate 5-8 flashcards from the following text for spaced repetition learning.
For each flashcard include:
1. front: The question or prompt (what to remember)
2. back: The answer or explanation
3. topic: The main topic/subject
4. tags: Array of related tags
5. difficulty: Difficulty level (beginner, intermediate, advanced)

Create flashcards that test understanding, not just recall.
Return as JSON array.

Text:
{text[:5000]}

Example output:
[
  {{
    "front": "What is backpropagation?",
    "back": "An algorithm for training neural networks by propagating error gradients backwards through the network",
    "topic": "Neural Networks",
    "tags": ["deep learning", "optimization", "training"],
    "difficulty": "intermediate"
  }}
]"""
        
        system_prompt = """You are an expert at creating effective flashcards for learning.
Create clear, focused flashcards that test deep understanding.
Return valid JSON arrays only."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            flashcards = json.loads(response)
            
            validated_flashcards = []
            for fc in flashcards:
                if self._validate_flashcard(fc):
                    validated_flashcards.append({
                        "front": fc.get("front", ""),
                        "back": fc.get("back", ""),
                        "topic": fc.get("topic"),
                        "tags": fc.get("tags", []),
                        "difficulty": fc.get("difficulty", DifficultyLevel.INTERMEDIATE.value),
                        "confidence_score": 0.7,
                    })
            
            context.emit_progress(
                self.service_name, 1.0,
                f"Generated {len(validated_flashcards)} flashcards"
            )
            
            return validated_flashcards
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse flashcard generation response: {e}")
            return []
        except Exception as e:
            logger.error(f"Flashcard generation failed: {e}")
            return []
    
    def _validate_flashcard(self, flashcard: Dict) -> bool:
        """Validate a generated flashcard."""
        if not flashcard.get("front") or not flashcard.get("back"):
            return False
        if len(flashcard.get("front", "")) < 5:
            return False
        if len(flashcard.get("back", "")) < 5:
            return False
        return True
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at creating effective flashcards for learning.
Create clear, focused flashcards that test deep understanding.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock flashcard response for testing."""
        return """[
  {
    "front": "What is a neural network?",
    "back": "A computing system inspired by biological neural networks, consisting of interconnected nodes (neurons) that process information",
    "topic": "Neural Networks",
    "tags": ["AI", "deep learning", "machine learning"],
    "difficulty": "beginner"
  }
]"""
