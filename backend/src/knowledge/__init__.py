"""
Knowledge Intelligence Module

This module provides structured knowledge extraction and storage services.
Every uploaded document is processed through the knowledge pipeline to extract:
- Summaries (multiple levels)
- Entities (persons, organizations, technologies, etc.)
- Concepts (independent of entities)
- Relationships (between concepts/entities)
- Questions (for learning)
- Flashcards (for spaced repetition)
- Topics and categories
- Semantic tags (skills, technologies, industries)

All extracted knowledge is stored in structured database models
for consumption by future subsystems (NotebookLM, Deep Research, etc.)
"""

from src.knowledge.models import (
    DocumentSummary,
    KnowledgeEntity,
    KnowledgeConcept,
    KnowledgeRelationship,
    GeneratedQuestion,
    KnowledgeFlashcard,
    DocumentTopic,
    SemanticTag,
    DocumentSection,
    KnowledgeMetadata,
)

from src.knowledge.extraction.summarizer import SummaryService
from src.knowledge.extraction.entity_extractor import EntityExtractionService
from src.knowledge.extraction.concept_extractor import ConceptExtractionService
from src.knowledge.extraction.relationship_extractor import RelationshipExtractionService
from src.knowledge.extraction.question_generator import QuestionGenerationService
from src.knowledge.extraction.flashcard_generator import FlashcardGenerationService
from src.knowledge.extraction.topic_classifier import TopicClassificationService
from src.knowledge.extraction.semantic_tagger import SemanticTaggingService
from src.knowledge.extraction.metadata_extractor import MetadataExtractionService

from src.knowledge.processing.pipeline import KnowledgeIntelligencePipeline

__all__ = [
    # Models
    "DocumentSummary",
    "KnowledgeEntity",
    "KnowledgeConcept",
    "KnowledgeRelationship",
    "GeneratedQuestion",
    "KnowledgeFlashcard",
    "DocumentTopic",
    "SemanticTag",
    "DocumentSection",
    "KnowledgeMetadata",
    # Services
    "SummaryService",
    "EntityExtractionService",
    "ConceptExtractionService",
    "RelationshipExtractionService",
    "QuestionGenerationService",
    "FlashcardGenerationService",
    "TopicClassificationService",
    "SemanticTaggingService",
    "MetadataExtractionService",
    # Pipeline
    "KnowledgeIntelligencePipeline",
]
