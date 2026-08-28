"""
Question Generation Service

Generates learning questions from document content.
"""

import json
from typing import List, Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.knowledge.models import QuestionType, DifficultyLevel
from src.core.logging import logger


class QuestionGenerationService(BaseExtractionService):
    """
    Service for generating learning questions from documents.
    
    Generates questions at different difficulty levels:
    - Beginner
    - Intermediate
    - Advanced
    
    And different types:
    - Multiple Choice (MCQ)
    - Short Answer
    - Conceptual
    - Analytical
    - Scenario Based
    """
    
    service_name = "question_generation"
    estimated_time_ms = 25000
    
    def _extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Generate learning questions from document text.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            List of generated questions with answers
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.1, "Generating beginner questions...")
        
        # Generate questions at each difficulty level
        all_questions = []
        
        # Beginner questions
        beginner = self._generate_questions_by_difficulty(
            text, DifficultyLevel.BEGINNER, count=3
        )
        all_questions.extend(beginner)
        
        context.emit_progress(self.service_name, 0.4, "Generating intermediate questions...")
        
        # Intermediate questions
        intermediate = self._generate_questions_by_difficulty(
            text, DifficultyLevel.INTERMEDIATE, count=3
        )
        all_questions.extend(intermediate)
        
        context.emit_progress(self.service_name, 0.7, "Generating advanced questions...")
        
        # Advanced questions
        advanced = self._generate_questions_by_difficulty(
            text, DifficultyLevel.ADVANCED, count=2
        )
        all_questions.extend(advanced)
        
        context.emit_progress(
            self.service_name, 1.0,
            f"Generated {len(all_questions)} questions"
        )
        
        return all_questions
    
    def _generate_questions_by_difficulty(
        self, 
        text: str, 
        difficulty: DifficultyLevel,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate questions at a specific difficulty level."""
        
        difficulty_prompt = {
            DifficultyLevel.BEGINNER: "basic factual questions about the main topics",
            DifficultyLevel.INTERMEDIATE: "questions requiring understanding and application",
            DifficultyLevel.ADVANCED: "complex analytical and synthesis questions"
        }
        
        prompt = f"""Generate {count} {difficulty.value} level questions from the following text.
For each question include:
1. question_text: The question itself
2. question_type: Type of question (multiple_choice, short_answer, conceptual)
3. difficulty: The difficulty level ({difficulty.value})
4. answer: The correct answer (for short answer) or explanation
5. options: Array of 4 options (for multiple choice, leave null for others)
6. correct_option_index: Index of correct option (0-3, null for non-MCQ)
7. topic: The main topic this question relates to

Return as JSON array.

Text:
{text[:5000]}

Example output:
[
  {{
    "question_text": "What is the primary purpose of neural networks?",
    "question_type": "multiple_choice",
    "difficulty": "beginner",
    "answer": "To learn patterns from data",
    "options": ["To store data", "To learn patterns from data", "To display graphics", "To manage files"],
    "correct_option_index": 1,
    "topic": "Neural Networks"
  }}
]"""
        
        system_prompt = f"""You are an expert at creating educational questions.
Generate {difficulty_prompt.get(difficulty, 'questions')} from the content.
Return valid JSON arrays only."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            questions = json.loads(response)
            
            validated_questions = []
            for q in questions:
                if self._validate_question(q):
                    validated_questions.append({
                        "question_text": q.get("question_text", ""),
                        "question_type": q.get("question_type", QuestionType.SHORT_ANSWER.value),
                        "difficulty": difficulty.value,
                        "answer": q.get("answer"),
                        "options": q.get("options"),
                        "correct_option_index": q.get("correct_option_index"),
                        "topic": q.get("topic"),
                        "confidence_score": 0.7,
                    })
            
            return validated_questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse question generation response: {e}")
            return []
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            return []
    
    def _validate_question(self, question: Dict) -> bool:
        """Validate a generated question."""
        if not question.get("question_text"):
            return False
        if len(question.get("question_text", "")) < 10:
            return False
        return True
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at creating educational questions.
Generate clear, well-formed questions with accurate answers.
Return valid JSON arrays only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock question response for testing."""
        return """[
  {
    "question_text": "What is machine learning?",
    "question_type": "multiple_choice",
    "difficulty": "beginner",
    "answer": "A type of AI that learns from data",
    "options": ["A programming language", "A type of AI that learns from data", "A database", "A web framework"],
    "correct_option_index": 1,
    "topic": "Machine Learning"
  }
]"""
