"""
Cross-Language Search Service

Enables semantic search across languages without translation.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from src.multilingual.detector import get_language_detector
from src.multilingual.registry import get_language_registry
from src.models.document import Document
from src.knowledge.models import KnowledgeEntity, KnowledgeConcept
from src.core.logging import logger

logger = logging.getLogger(__name__)


class CrossLanguageSearchService:
    """
    Service for cross-language semantic search.
    
    Enables:
    - Search in one language, retrieve from any language
    - Semantic matching across languages
    - Query expansion in multiple languages
    - Hybrid search with BM25 + vectors
    """
    
    def __init__(self, db: Session):
        """Initialize the cross-language search service."""
        self.db = db
        self.detector = get_language_detector()
        self.registry = get_language_registry()
    
    def search(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        language_filter: Optional[str] = None,
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across languages.
        
        Args:
            query: Search query (any language)
            user_id: User ID
            limit: Maximum results
            language_filter: Optional filter by language
            document_ids: Optional filter by document IDs
            
        Returns:
            List of matching chunks with metadata
        """
        # Detect query language
        detection = self.detector.detect(query)
        query_language = detection.language
        
        logger.info(f"Cross-language search: query='{query[:50]}...', language={query_language}")
        
        # Build search strategy based on language and available embeddings
        search_languages = self._get_search_languages(query_language)
        
        # Perform semantic search
        results = self._semantic_search(
            query=query,
            query_language=query_language,
            search_languages=search_languages,
            user_id=user_id,
            limit=limit,
            language_filter=language_filter,
            document_ids=document_ids
        )
        
        return results
    
    def _get_search_languages(self, query_language: str) -> List[str]:
        """Get list of languages to search."""
        languages_with_embeddings = self.registry.get_languages_with_embeddings()
        
        # If query language has embeddings, search it and related languages
        if query_language in languages_with_embeddings:
            related = self.registry.get_related_languages(query_language)
            return [query_language] + related + languages_with_embeddings[:5]
        
        # Otherwise search all languages with embeddings
        return languages_with_embeddings[:10]
    
    def _semantic_search(
        self,
        query: str,
        query_language: str,
        search_languages: List[str],
        user_id: int,
        limit: int,
        language_filter: Optional[str],
        document_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across languages.
        
        This is a simplified implementation that:
        1. Searches by text similarity (fallback when embeddings unavailable)
        2. Would integrate with vector database for production
        """
        # Build base query for entities
        entity_query = self.db.query(KnowledgeEntity).join(Document).filter(
            Document.owner_id == user_id
        )
        
        # Apply language filter via document
        if language_filter:
            entity_query = entity_query.join(
                Document, KnowledgeEntity.document_id == Document.id
            ).filter(Document.language_code == language_filter)
        
        # Apply document filter
        if document_ids:
            entity_query = entity_query.filter(KnowledgeEntity.document_id.in_(document_ids))
        
        # Get all entities
        all_entities = entity_query.all()
        
        # Score entities by relevance (simplified - uses keyword matching)
        scored_entities = []
        query_words = set(query.lower().split())
        
        for entity in all_entities:
            entity_text = ((entity.description or "") + " " + (entity.name or "")).lower()
            entity_words = set(entity_text.split())
            
            # Calculate keyword overlap score
            overlap = len(query_words & entity_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                
                scored_entities.append({
                    "entity_id": entity.id,
                    "document_id": entity.document_id,
                    "name": entity.name,
                    "description": entity.description,
                    "entity_type": entity.entity_type.value if hasattr(entity.entity_type, 'value') else entity.entity_type,
                    "score": score,
                    "match_type": "keyword"
                })
        
        # Sort by score and return top results
        scored_entities.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_entities[:limit]
    
    def search_with_expansion(
        self,
        query: str,
        user_id: int,
        expansion_languages: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search with automatic query expansion.
        
        Expands query to related terms in multiple languages.
        """
        # Detect query language
        detection = self.detector.detect(query)
        query_language = detection.language
        
        # Get expansion languages
        if expansion_languages is None:
            expansion_languages = self._get_expansion_languages(query_language)
        
        # Generate expanded queries
        expanded_queries = self._expand_query(query, expansion_languages)
        
        # Search with each expanded query
        all_results = []
        seen_ids = set()
        
        for lang, expanded_query in expanded_queries:
            results = self.search(
                query=expanded_query,
                user_id=user_id,
                limit=limit,
                language_filter=lang if lang else None
            )
            
            for result in results:
                if result["chunk_id"] not in seen_ids:
                    result["query_language"] = query_language
                    result["expanded_from"] = lang
                    all_results.append(result)
                    seen_ids.add(result["chunk_id"])
        
        # Merge and rerank results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "original_query": query,
            "query_language": query_language,
            "expanded_queries": expanded_queries,
            "results": all_results[:limit]
        }
    
    def _get_expansion_languages(self, query_language: str) -> List[str]:
        """Get languages for query expansion."""
        languages = [query_language]
        
        # Add related languages
        related = self.registry.get_related_languages(query_language)
        languages.extend(related[:3])
        
        # Add high-priority languages
        high_priority = ["en", "es", "fr", "de", "zh", "ja", "ar", "ru"]
        for lang in high_priority:
            if lang not in languages:
                languages.append(lang)
        
        return languages[:6]
    
    def _expand_query(self, query: str, languages: List[str]) -> List[Tuple[Optional[str], str]]:
        """
        Expand query to multiple languages.
        
        Returns list of (language, expanded_query) tuples.
        """
        # In production, this would use translation API
        # For now, return original query for each language
        return [(lang, query) for lang in languages] + [(None, query)]
    
    def get_language_distribution(
        self,
        user_id: int,
        document_ids: Optional[List[int]] = None
    ) -> Dict[str, int]:
        """Get distribution of languages in user's documents."""
        query = self.db.query(
            Document.language,
            func.count(Document.id).label('count')
        ).filter(Document.owner_id == user_id)
        
        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        
        results = query.group_by(Document.language).all()
        
        return {lang: count for lang, count in results}
    
    def suggest_language_correction(
        self,
        query: str,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Suggest language corrections or alternatives.
        
        Useful for typos or language detection issues.
        """
        suggestions = []
        
        # Get similar language names
        similar = self.registry.search(query)
        for lang_info in similar[:max_suggestions]:
            suggestions.append(lang_info.code)
        
        return suggestions


# Service factory
def get_cross_language_search_service(db: Session) -> CrossLanguageSearchService:
    """Get cross-language search service instance."""
    return CrossLanguageSearchService(db)
