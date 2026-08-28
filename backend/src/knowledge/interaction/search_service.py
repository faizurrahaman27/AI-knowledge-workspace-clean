"""
Semantic Search Service

Provides unified search across all knowledge types.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from src.knowledge.models import (
    KnowledgeEntity, KnowledgeConcept, KnowledgeRelationship,
    GeneratedQuestion, KnowledgeFlashcard, DocumentTopic, SemanticTag
)
from src.knowledge.interaction_models import KnowledgeNote
from src.knowledge.validation_models import KnowledgeCitation
from src.models.document import Document
from src.core.logging import logger


class SemanticSearchService:
    """
    Service for semantic search across all knowledge.
    
    Searches:
    - Documents
    - Concepts
    - Entities
    - Notes
    - Questions
    - Flashcards
    - Topics
    - Collections
    """
    
    def __init__(self, db: Session):
        """Initialize the search service."""
        self.db = db
    
    def search(
        self,
        user_id: int,
        query: str,
        search_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across all knowledge types.
        
        Args:
            user_id: User ID
            query: Search query
            search_types: Types to search (if None, search all)
            limit: Maximum results per type
            
        Returns:
            Dictionary mapping type to results
        """
        results = {}
        search_pattern = f"%{query}%"
        
        # Default to searching all types
        if search_types is None:
            search_types = [
                "documents", "concepts", "entities", "notes",
                "questions", "flashcards", "topics"
            ]
        
        if "documents" in search_types:
            results["documents"] = self._search_documents(user_id, search_pattern, limit)
        
        if "concepts" in search_types:
            results["concepts"] = self._search_concepts(user_id, search_pattern, limit)
        
        if "entities" in search_types:
            results["entities"] = self._search_entities(user_id, search_pattern, limit)
        
        if "notes" in search_types:
            results["notes"] = self._search_notes(user_id, search_pattern, limit)
        
        if "questions" in search_types:
            results["questions"] = self._search_questions(user_id, search_pattern, limit)
        
        if "flashcards" in search_types:
            results["flashcards"] = self._search_flashcards(user_id, search_pattern, limit)
        
        if "topics" in search_types:
            results["topics"] = self._search_topics(user_id, search_pattern, limit)
        
        return results
    
    def _search_documents(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search documents."""
        docs = self.db.query(Document).filter(
            Document.owner_id == user_id,
            or_(
                Document.title.ilike(pattern),
                Document.original_filename.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": d.id,
                "title": d.title,
                "filename": d.original_filename,
                "content_type": d.content_type,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in docs
        ]
    
    def _search_concepts(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search concepts."""
        concepts = self.db.query(KnowledgeConcept).join(Document).filter(
            Document.owner_id == user_id,
            or_(
                KnowledgeConcept.name.ilike(pattern),
                KnowledgeConcept.description.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "importance": c.importance,
                "difficulty": c.difficulty,
                "document_id": c.document_id,
                "confidence_score": c.confidence_score
            }
            for c in concepts
        ]
    
    def _search_entities(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search entities."""
        entities = self.db.query(KnowledgeEntity).join(Document).filter(
            Document.owner_id == user_id,
            or_(
                KnowledgeEntity.name.ilike(pattern),
                KnowledgeEntity.description.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "description": e.description,
                "document_id": e.document_id,
                "mentions": e.mentions
            }
            for e in entities
        ]
    
    def _search_notes(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search notes."""
        notes = self.db.query(KnowledgeNote).filter(
            KnowledgeNote.user_id == user_id,
            KnowledgeNote.is_archived == False,
            or_(
                KnowledgeNote.title.ilike(pattern),
                KnowledgeNote.content.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": n.id,
                "title": n.title,
                "content_preview": n.content[:200] if n.content else "",
                "note_type": n.note_type,
                "is_pinned": n.is_pinned,
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notes
        ]
    
    def _search_questions(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search questions."""
        questions = self.db.query(GeneratedQuestion).join(Document).filter(
            Document.owner_id == user_id,
            or_(
                GeneratedQuestion.question_text.ilike(pattern),
                GeneratedQuestion.answer.ilike(pattern),
                GeneratedQuestion.topic.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": q.id,
                "question_text": q.question_text,
                "answer": q.answer,
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "topic": q.topic,
                "document_id": q.document_id
            }
            for q in questions
        ]
    
    def _search_flashcards(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search flashcards."""
        flashcards = self.db.query(KnowledgeFlashcard).join(Document).filter(
            Document.owner_id == user_id,
            or_(
                KnowledgeFlashcard.front.ilike(pattern),
                KnowledgeFlashcard.back.ilike(pattern),
                KnowledgeFlashcard.topic.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": f.id,
                "front": f.front,
                "back": f.back,
                "topic": f.topic,
                "difficulty": f.difficulty,
                "document_id": f.document_id
            }
            for f in flashcards
        ]
    
    def _search_topics(
        self,
        user_id: int,
        pattern: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search topics."""
        topics = self.db.query(DocumentTopic).join(Document).filter(
            Document.owner_id == user_id,
            or_(
                DocumentTopic.topic_name.ilike(pattern),
                DocumentTopic.category.ilike(pattern)
            )
        ).limit(limit).all()
        
        return [
            {
                "id": t.id,
                "topic_name": t.topic_name,
                "category": t.category,
                "subcategory": t.subcategory,
                "topic_type": t.topic_type,
                "importance_score": t.importance_score
            }
            for t in topics
        ]
    
    def unified_search(
        self,
        user_id: int,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Unified search across all types.
        
        Returns flat list sorted by relevance.
        """
        results = self.search(user_id, query, limit=limit)
        
        unified = []
        
        for type_name, items in results.items():
            for item in items:
                unified.append({
                    "type": type_name,
                    "id": item["id"],
                    "title": item.get("title") or item.get("name") or item.get("topic_name") or item.get("question_text") or item.get("front", ""),
                    "description": self._get_description(item, type_name),
                    "data": item
                })
        
        # Sort by type (documents first, then concepts, etc.)
        type_order = ["documents", "concepts", "entities", "notes", "questions", "flashcards", "topics"]
        
        unified.sort(key=lambda x: (
            type_order.index(x["type"]) if x["type"] in type_order else len(type_order)
        ))
        
        return unified[:limit]
    
    def _get_description(self, item: Dict, item_type: str) -> str:
        """Get description for item."""
        if item_type == "documents":
            return item.get("filename", "")
        elif item_type == "concepts":
            return item.get("description", "")[:100]
        elif item_type == "entities":
            return f"{item.get('entity_type', 'entity')}: {item.get('description', '')[:100]}"
        elif item_type == "notes":
            return item.get("content_preview", "")[:100]
        elif item_type == "questions":
            return item.get("answer", "")[:100]
        elif item_type == "flashcards":
            return f"Topic: {item.get('topic', '')}"
        elif item_type == "topics":
            return f"{item.get('category', '')} / {item.get('subcategory', '')}"
        return ""
    
    def search_by_tag(
        self,
        user_id: int,
        tag: str,
        limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search by semantic tag."""
        tag_pattern = f'%"{tag}"%'
        
        results = {}
        
        # Search semantic tags
        tags = self.db.query(SemanticTag).join(Document).filter(
            Document.owner_id == user_id,
            SemanticTag.tag.ilike(tag_pattern)
        ).limit(limit).all()
        
        # Get documents for these tags
        doc_ids = list(set([t.document_id for t in tags]))
        
        if doc_ids:
            docs = self.db.query(Document).filter(
                Document.id.in_(doc_ids),
                Document.owner_id == user_id
            ).limit(limit).all()
            
            results["documents"] = [
                {"id": d.id, "title": d.title, "filename": d.original_filename}
                for d in docs
            ]
        
        results["tags"] = [
            {
                "id": t.id,
                "tag": t.tag,
                "tag_category": t.tag_category,
                "relevance_score": t.relevance_score,
                "document_id": t.document_id
            }
            for t in tags[:20]
        ]
        
        return results
    
    def get_search_suggestions(
        self,
        user_id: int,
        partial_query: str,
        limit: int = 10
    ) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = set()
        pattern = f"{partial_query}%"
        
        # Get concept names
        concepts = self.db.query(KnowledgeConcept.name).join(Document).filter(
            Document.owner_id == user_id,
            KnowledgeConcept.name.ilike(pattern)
        ).limit(5).all()
        
        for c in concepts:
            suggestions.add(c.name)
        
        # Get entity names
        entities = self.db.query(KnowledgeEntity.name).join(Document).filter(
            Document.owner_id == user_id,
            KnowledgeEntity.name.ilike(pattern)
        ).limit(5).all()
        
        for e in entities:
            suggestions.add(e.name)
        
        # Get topic names
        topics = self.db.query(DocumentTopic.topic_name).join(Document).filter(
            Document.owner_id == user_id,
            DocumentTopic.topic_name.ilike(pattern)
        ).limit(5).all()
        
        for t in topics:
            suggestions.add(t.topic_name)
        
        # Get note titles
        notes = self.db.query(KnowledgeNote.title).filter(
            KnowledgeNote.user_id == user_id,
            KnowledgeNote.title.ilike(pattern),
            KnowledgeNote.title.isnot(None)
        ).limit(5).all()
        
        for n in notes:
            if n.title:
                suggestions.add(n.title)
        
        return list(suggestions)[:limit]
