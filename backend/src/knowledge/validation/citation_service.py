"""
Citation Mapping Service

Maps extracted knowledge to its source locations in documents.
"""

from typing import List, Dict, Any, Optional
import re

from sqlalchemy.orm import Session

from src.knowledge.validation.base import BaseValidationService, ValidationContext, ValidationResult
from src.knowledge.validation_models import KnowledgeCitation, SourceType
from src.core.logging import logger


class CitationMappingService(BaseValidationService):
    """
    Maps extracted knowledge to source document locations.
    
    Each extracted piece of knowledge should have at least one citation
    pointing to its origin in the source document.
    """
    
    service_name = "citation_mapping"
    estimated_time_ms = 3000
    
    def __init__(self, db: Session):
        """
        Initialize the citation mapping service.
        
        Args:
            db: Database session
        """
        super().__init__()
        self.db = db
    
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """Validate citations for extracted knowledge."""
        # This service doesn't validate - it creates citations
        return ValidationResult(
            success=True,
            passed=True,
            message="Citation mapping service"
        )
    
    def create_citations(
        self,
        document_id: int,
        knowledge_type: str,
        knowledge_id: int,
        chunks: List[Dict[str, Any]],
        text: str,
        progress_callback: Optional[callable] = None
    ) -> List[KnowledgeCitation]:
        """
        Create citations for extracted knowledge.
        
        Args:
            document_id: Source document ID
            knowledge_type: Type of knowledge (entity, concept, etc.)
            knowledge_id: ID of the knowledge item
            chunks: List of text chunks with positions
            text: Full document text
            progress_callback: Optional progress callback
            
        Returns:
            List of created citations
        """
        citations = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            if progress_callback and total_chunks > 0:
                progress = (i / total_chunks) * 100
                progress_callback("citation_mapping", progress, f"Creating citations for chunk {i+1}/{total_chunks}")
            
            citation = self._create_citation_from_chunk(
                document_id=document_id,
                knowledge_type=knowledge_type,
                knowledge_id=knowledge_id,
                chunk=chunk,
                text=text
            )
            
            if citation:
                self.db.add(citation)
                citations.append(citation)
        
        try:
            self.db.commit()
            logger.info(f"Created {len(citations)} citations for {knowledge_type} {knowledge_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save citations: {e}")
        
        return citations
    
    def _create_citation_from_chunk(
        self,
        document_id: int,
        knowledge_type: str,
        knowledge_id: int,
        chunk: Dict[str, Any],
        text: str
    ) -> Optional[KnowledgeCitation]:
        """Create a single citation from a chunk."""
        try:
            page_number = chunk.get("page")
            chunk_index = chunk.get("chunk_index", 0)
            chunk_text = chunk.get("text", "")
            
            # Find the text excerpt
            text_excerpt = self._extract_relevant_excerpt(text, chunk_text)
            
            citation = KnowledgeCitation(
                knowledge_type=knowledge_type,
                knowledge_id=knowledge_id,
                document_id=document_id,
                source_type=SourceType.CHUNK.value,
                source_id=f"chunk_{chunk_index}",
                page_number=page_number,
                chunk_index=chunk_index,
                text_excerpt=text_excerpt,
                relevance_score=0.8,  # Default relevance
                is_primary=True
            )
            
            return citation
            
        except Exception as e:
            logger.error(f"Failed to create citation: {e}")
            return None
    
    def _extract_relevant_excerpt(
        self,
        full_text: str,
        chunk_text: str,
        max_length: int = 200
    ) -> str:
        """Extract relevant excerpt from chunk text."""
        if not chunk_text:
            return ""
        
        # Clean up the text
        excerpt = chunk_text.strip()
        
        # Limit length
        if len(excerpt) > max_length:
            excerpt = excerpt[:max_length] + "..."
        
        return excerpt
    
    def get_citations_for_knowledge(
        self,
        knowledge_type: str,
        knowledge_id: int
    ) -> List[KnowledgeCitation]:
        """Get all citations for a knowledge item."""
        return self.db.query(KnowledgeCitation).filter(
            KnowledgeCitation.knowledge_type == knowledge_type,
            KnowledgeCitation.knowledge_id == knowledge_id
        ).order_by(KnowledgeCitation.relevance_score.desc()).all()
    
    def get_citations_for_document(
        self,
        document_id: int
    ) -> List[KnowledgeCitation]:
        """Get all citations for a document."""
        return self.db.query(KnowledgeCitation).filter(
            KnowledgeCitation.document_id == document_id
        ).all()
    
    def calculate_citation_coverage(
        self,
        document_id: int,
        total_knowledge_items: int
    ) -> float:
        """Calculate the percentage of knowledge with citations."""
        if total_knowledge_items == 0:
            return 0.0
        
        cited_count = self.db.query(KnowledgeCitation).filter(
            KnowledgeCitation.document_id == document_id
        ).count()
        
        # Divide by knowledge types (rough estimate)
        estimated_knowledge_types = 5  # entities, concepts, relationships, etc.
        estimated_total = total_knowledge_items * estimated_knowledge_types
        
        return min(cited_count / max(estimated_total, 1), 1.0)
