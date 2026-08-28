"""
Knowledge Intelligence Pipeline

Orchestrates the complete knowledge extraction pipeline.
Each document goes through multiple stages of analysis.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any
import time

from sqlalchemy.orm import Session

from src.core.logging import logger
from src.models.document import Document

from src.knowledge.extraction.base import ExtractionContext, ExtractionResult
from src.knowledge.extraction.summarizer import SummaryService
from src.knowledge.extraction.entity_extractor import EntityExtractionService
from src.knowledge.extraction.concept_extractor import ConceptExtractionService
from src.knowledge.extraction.relationship_extractor import RelationshipExtractionService
from src.knowledge.extraction.question_generator import QuestionGenerationService
from src.knowledge.extraction.flashcard_generator import FlashcardGenerationService
from src.knowledge.extraction.topic_classifier import TopicClassificationService
from src.knowledge.extraction.semantic_tagger import SemanticTaggingService
from src.knowledge.extraction.metadata_extractor import MetadataExtractionService

from src.knowledge.models import (
    DocumentSummary, KnowledgeEntity, KnowledgeConcept,
    KnowledgeRelationship, GeneratedQuestion, KnowledgeFlashcard,
    DocumentTopic, SemanticTag, DocumentSection, KnowledgeMetadata
)


class KnowledgeIntelligencePipeline:
    """
    Orchestrates the complete knowledge extraction pipeline.
    
    Pipeline stages:
    1. Text extraction (already done in ingestion)
    2. Metadata extraction
    3. Topic classification
    4. Summary generation
    5. Entity extraction
    6. Concept extraction
    7. Relationship extraction
    8. Question generation
    9. Flashcard generation
    10. Semantic tagging
    
    Each stage can be configured independently.
    """
    
    def __init__(
        self,
        db: Session,
        llm_provider=None,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the knowledge intelligence pipeline.
        
        Args:
            db: Database session
            llm_provider: Optional LLM provider for extraction
            progress_callback: Optional callback for progress updates
        """
        self.db = db
        self.llm_provider = llm_provider
        self.progress_callback = progress_callback
        
        # Initialize extraction services
        self.services = {
            "metadata": MetadataExtractionService(),
            "topics": TopicClassificationService(llm_provider),
            "summary": SummaryService(llm_provider),
            "entities": EntityExtractionService(llm_provider),
            "concepts": ConceptExtractionService(llm_provider),
            "relationships": RelationshipExtractionService(llm_provider),
            "questions": QuestionGenerationService(llm_provider),
            "flashcards": FlashcardGenerationService(llm_provider),
            "semantic_tags": SemanticTaggingService(llm_provider),
        }
        
        # Stage weights for progress calculation
        self.stage_weights = {
            "metadata": 0.05,
            "topics": 0.08,
            "summary": 0.12,
            "entities": 0.15,
            "concepts": 0.15,
            "relationships": 0.15,
            "questions": 0.10,
            "flashcards": 0.10,
            "semantic_tags": 0.10,
        }
    
    def _emit_progress(self, stage: str, progress: float, message: str, data: Dict = None):
        """Emit progress update."""
        if self.progress_callback:
            self.progress_callback(stage, progress, message, data)
        
        logger.info(f"[Pipeline] {stage}: {message} ({progress:.0%})")
    
    async def process_document(self, document: Document) -> bool:
        """
        Process a document through the knowledge intelligence pipeline.
        
        Args:
            document: Document to process
            
        Returns:
            True if processing succeeded, False otherwise
        """
        start_time = time.time()
        document_id = document.id
        
        try:
            # Update document status
            document.knowledge_extracted = 1  # In progress
            self.db.commit()
            
            self._emit_progress("pipeline", 0.0, f"Starting knowledge extraction for document {document_id}")
            
            # Get document text
            text = self._get_document_text(document)
            if not text or len(text) < 100:
                logger.warning(f"Document {document_id} has insufficient text for processing")
                document.extraction_error = "Insufficient text content"
                self.db.commit()
                return False
            
            # Create extraction context
            context = ExtractionContext(
                document_id=document_id,
                text=text,
                language_code=document.language_code,
                progress_callback=lambda s, p, m: self._emit_progress(s, p * self.stage_weights.get(s, 0.1), m)
            )
            
            # Process stages
            results = {}
            cumulative_progress = 0.0
            
            for stage_name, service in self.services.items():
                self._emit_progress(
                    stage_name, 
                    cumulative_progress,
                    f"Starting {stage_name} extraction..."
                )
                
                result = service.extract(context)
                results[stage_name] = result
                
                if result.success:
                    # Store results in database
                    await self._store_results(document, stage_name, result.data)
                
                cumulative_progress += self.stage_weights.get(stage_name, 0.1)
                
                self._emit_progress(
                    stage_name,
                    cumulative_progress,
                    f"Completed {stage_name} extraction" + (f" ({len(result.data) if result.data else 0} items)" if isinstance(result.data, list) else "")
                )
            
            # Update document status
            document.knowledge_extracted = 2  # Complete
            document.extraction_error = None
            self.db.commit()
            
            processing_time = time.time() - start_time
            self._emit_progress(
                "pipeline",
                1.0,
                f"Knowledge extraction complete for document {document_id} in {processing_time:.1f}s"
            )
            
            return True
            
        except Exception as e:
            logger.exception(f"Knowledge extraction failed for document {document_id}")
            document.knowledge_extracted = 0
            document.extraction_error = str(e)
            self.db.commit()
            return False
    
    def _get_document_text(self, document: Document) -> str:
        """Extract text content from document."""
        try:
            if document.file_path and document.content_type == "text/plain":
                with open(document.file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            elif document.file_path:
                # For other formats, return empty (text already extracted during ingestion)
                # In a real implementation, we'd store the extracted text
                return ""
        except Exception as e:
            logger.error(f"Failed to read document text: {e}")
        return ""
    
    async def _store_results(
        self, 
        document: Document, 
        stage_name: str, 
        data: Any
    ):
        """Store extraction results in database."""
        try:
            if stage_name == "metadata" and data:
                self._store_metadata(document, data)
            elif stage_name == "summary" and data:
                self._store_summary(document, data)
            elif stage_name == "entities" and data:
                self._store_entities(document, data)
            elif stage_name == "concepts" and data:
                self._store_concepts(document, data)
            elif stage_name == "relationships" and data:
                self._store_relationships(document, data)
            elif stage_name == "questions" and data:
                self._store_questions(document, data)
            elif stage_name == "flashcards" and data:
                self._store_flashcards(document, data)
            elif stage_name == "topics" and data:
                self._store_topics(document, data)
            elif stage_name == "semantic_tags" and data:
                self._store_semantic_tags(document, data)
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store {stage_name} results: {e}")
            self.db.rollback()
    
    def _store_metadata(self, document: Document, data: Dict):
        """Store metadata extraction results."""
        # Check if metadata exists
        metadata = document.knowledge_metadata
        
        if not metadata:
            metadata = KnowledgeMetadata(document_id=document.id)
            self.db.add(metadata)
        
        metadata.word_count = data.get("word_count")
        metadata.sentence_count = data.get("sentence_count")
        metadata.paragraph_count = data.get("paragraph_count")
        metadata.reading_time_minutes = data.get("reading_time_minutes")
        metadata.difficulty_score = data.get("difficulty_score")
        metadata.document_category = data.get("document_category")
        metadata.academic_subject = data.get("academic_subject")
        metadata.language = data.get("language")
        metadata.language_name = data.get("language_name")
        metadata.extraction_complete = True
        metadata.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def _store_summary(self, document: Document, data: Dict):
        """Store summary extraction results."""
        # Delete existing summary
        if document.summary:
            self.db.delete(document.summary)
        
        summary = DocumentSummary(
            document_id=document.id,
            one_sentence_summary=data.get("one_sentence_summary"),
            executive_summary=data.get("executive_summary"),
            bullet_summary=data.get("bullet_summary"),
            detailed_summary=data.get("detailed_summary"),
            version=1
        )
        self.db.add(summary)
    
    def _store_entities(self, document: Document, data: list):
        """Store entity extraction results."""
        for entity_data in data[:100]:  # Limit to 100 entities
            entity = KnowledgeEntity(
                document_id=document.id,
                name=entity_data.get("name", ""),
                entity_type=entity_data.get("entity_type", "other"),
                canonical_name=entity_data.get("canonical_name"),
                description=entity_data.get("description"),
                mentions=entity_data.get("mentions", 1),
                confidence_score=entity_data.get("confidence_score", 0.7)
            )
            self.db.add(entity)
    
    def _store_concepts(self, document: Document, data: list):
        """Store concept extraction results."""
        for concept_data in data[:50]:  # Limit to 50 concepts
            concept = KnowledgeConcept(
                document_id=document.id,
                name=concept_data.get("name", ""),
                description=concept_data.get("description"),
                importance=concept_data.get("importance", "medium"),
                difficulty=concept_data.get("difficulty", "intermediate"),
                related_concepts=concept_data.get("related_concepts", []),
                confidence_score=concept_data.get("confidence_score", 0.7)
            )
            self.db.add(concept)
    
    def _store_relationships(self, document: Document, data: list):
        """Store relationship extraction results."""
        for rel_data in data[:50]:  # Limit to 50 relationships
            relationship = KnowledgeRelationship(
                document_id=document.id,
                source_type=rel_data.get("source_type", "concept"),
                source_id=0,  # Will be resolved later
                source_name=rel_data.get("source_name", ""),
                relationship_type=rel_data.get("relationship_type", "related_to"),
                target_type=rel_data.get("target_type", "concept"),
                target_id=0,
                target_name=rel_data.get("target_name", ""),
                description=rel_data.get("description"),
                evidence=rel_data.get("evidence"),
                confidence_score=rel_data.get("confidence_score", 0.7),
                is_inferred=rel_data.get("is_inferred", False)
            )
            self.db.add(relationship)
    
    def _store_questions(self, document: Document, data: list):
        """Store question generation results."""
        for q_data in data[:20]:  # Limit to 20 questions
            question = GeneratedQuestion(
                document_id=document.id,
                question_text=q_data.get("question_text", ""),
                question_type=q_data.get("question_type", "short_answer"),
                difficulty=q_data.get("difficulty", "intermediate"),
                answer=q_data.get("answer"),
                options=q_data.get("options"),
                correct_option_index=q_data.get("correct_option_index"),
                topic=q_data.get("topic"),
                confidence_score=q_data.get("confidence_score", 0.7)
            )
            self.db.add(question)
    
    def _store_flashcards(self, document: Document, data: list):
        """Store flashcard generation results."""
        for fc_data in data[:20]:  # Limit to 20 flashcards
            flashcard = KnowledgeFlashcard(
                document_id=document.id,
                front=fc_data.get("front", ""),
                back=fc_data.get("back", ""),
                topic=fc_data.get("topic"),
                tags=fc_data.get("tags", []),
                difficulty=fc_data.get("difficulty", "intermediate"),
                confidence_score=fc_data.get("confidence_score", 0.7)
            )
            self.db.add(flashcard)
    
    def _store_topics(self, document: Document, data: list):
        """Store topic classification results."""
        for topic_data in data[:10]:  # Limit to 10 topics
            topic = DocumentTopic(
                document_id=document.id,
                topic_name=topic_data.get("topic_name", ""),
                topic_type=topic_data.get("topic_type", "secondary"),
                category=topic_data.get("category"),
                subcategory=topic_data.get("subcategory"),
                hierarchy_path=topic_data.get("hierarchy_path", []),
                prerequisite_topics=topic_data.get("prerequisite_topics", []),
                related_topics=topic_data.get("related_topics", []),
                confidence_score=topic_data.get("confidence_score", 0.7),
                importance_score=topic_data.get("importance_score", 0.5)
            )
            self.db.add(topic)
    
    def _store_semantic_tags(self, document: Document, data: list):
        """Store semantic tagging results."""
        for tag_data in data[:30]:  # Limit to 30 tags
            tag = SemanticTag(
                document_id=document.id,
                tag=tag_data.get("tag", ""),
                tag_category=tag_data.get("tag_category", "skill"),
                context=tag_data.get("context"),
                relevance_score=tag_data.get("relevance_score", 0.7)
            )
            self.db.add(tag)


async def run_knowledge_extraction(
    db: Session,
    document_id: int,
    llm_provider=None,
    progress_callback: Optional[Callable] = None
) -> bool:
    """
    Convenience function to run knowledge extraction on a document.
    
    Args:
        db: Database session
        document_id: ID of document to process
        llm_provider: Optional LLM provider
        progress_callback: Optional progress callback
        
    Returns:
        True if successful, False otherwise
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        logger.error(f"Document {document_id} not found")
        return False
    
    pipeline = KnowledgeIntelligencePipeline(
        db=db,
        llm_provider=llm_provider,
        progress_callback=progress_callback
    )
    
    return await pipeline.process_document(document)
