"""
Knowledge Extraction Services

Modular services for extracting structured knowledge from documents.
Each service is independently testable and replaceable.
"""

from src.knowledge.extraction.summarizer import SummaryService
from src.knowledge.extraction.entity_extractor import EntityExtractionService
from src.knowledge.extraction.concept_extractor import ConceptExtractionService
from src.knowledge.extraction.relationship_extractor import RelationshipExtractionService
from src.knowledge.extraction.question_generator import QuestionGenerationService
from src.knowledge.extraction.flashcard_generator import FlashcardGenerationService
from src.knowledge.extraction.topic_classifier import TopicClassificationService
from src.knowledge.extraction.semantic_tagger import SemanticTaggingService
from src.knowledge.extraction.metadata_extractor import MetadataExtractionService

__all__ = [
    "SummaryService",
    "EntityExtractionService",
    "ConceptExtractionService",
    "RelationshipExtractionService",
    "QuestionGenerationService",
    "FlashcardGenerationService",
    "TopicClassificationService",
    "SemanticTaggingService",
    "MetadataExtractionService",
]
