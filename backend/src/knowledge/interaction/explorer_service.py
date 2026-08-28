"""
Knowledge Explorer Service

Provides exploration capabilities for validated knowledge.
"""

from typing import List, Optional, Dict, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.knowledge.models import (
    KnowledgeEntity, KnowledgeConcept, KnowledgeRelationship,
    GeneratedQuestion, KnowledgeFlashcard, DocumentTopic, SemanticTag
)
from src.knowledge.validation_models import KnowledgeCitation, KnowledgeQuality
from src.knowledge.interaction_models import KnowledgeNote
from src.models.document import Document
from src.core.logging import logger


class KnowledgeExplorerService:
    """
    Service for exploring validated knowledge.
    
    Provides:
    - Browse by topics, concepts, entities, relationships
    - View related knowledge
    - Knowledge graph preview
    """
    
    def __init__(self, db: Session):
        """Initialize the explorer service."""
        self.db = db
    
    def get_topics_overview(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get overview of topics across user's documents."""
        topics = self.db.query(
            DocumentTopic.topic_name,
            DocumentTopic.category,
            DocumentTopic.topic_type,
            func.count(DocumentTopic.id).label('count')
        ).join(Document).filter(
            Document.owner_id == user_id
        ).group_by(
            DocumentTopic.topic_name,
            DocumentTopic.category,
            DocumentTopic.topic_type
        ).order_by(
            func.count(DocumentTopic.id).desc()
        ).limit(limit).all()
        
        return [
            {
                "topic_name": t.topic_name,
                "category": t.category,
                "topic_type": t.topic_type,
                "document_count": t.count
            }
            for t in topics
        ]
    
    def get_concepts_by_topic(
        self,
        user_id: int,
        topic_name: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get concepts related to a topic."""
        # Get documents with this topic
        topic_docs = self.db.query(DocumentTopic.document_id).filter(
            DocumentTopic.topic_name == topic_name
        ).subquery()
        
        concepts = self.db.query(KnowledgeConcept).join(Document).filter(
            Document.owner_id == user_id,
            Document.id.in_(topic_docs)
        ).order_by(
            KnowledgeConcept.confidence_score.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "importance": c.importance,
                "difficulty": c.difficulty,
                "confidence_score": c.confidence_score,
                "related_concepts": c.related_concepts or []
            }
            for c in concepts
        ]
    
    def get_entities_by_type(
        self,
        user_id: int,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get entities by type."""
        query = self.db.query(KnowledgeEntity).join(Document).filter(
            Document.owner_id == user_id
        )
        
        if entity_type:
            query = query.filter(KnowledgeEntity.entity_type == entity_type)
        
        entities = query.order_by(
            KnowledgeEntity.confidence_score.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "description": e.description,
                "mentions": e.mentions,
                "confidence_score": e.confidence_score
            }
            for e in entities
        ]
    
    def get_entity_types(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all entity types with counts."""
        types = self.db.query(
            KnowledgeEntity.entity_type,
            func.count(KnowledgeEntity.id).label('count')
        ).join(Document).filter(
            Document.owner_id == user_id
        ).group_by(
            KnowledgeEntity.entity_type
        ).all()
        
        return [
            {"type": t.entity_type, "count": t.count}
            for t in types
        ]
    
    def get_relationships_overview(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get relationship overview."""
        relationships = self.db.query(KnowledgeRelationship).join(Document).filter(
            Document.owner_id == user_id
        ).order_by(
            KnowledgeRelationship.confidence_score.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": r.id,
                "source_name": r.source_name,
                "source_type": r.source_type,
                "relationship_type": r.relationship_type,
                "target_name": r.target_name,
                "target_type": r.target_type,
                "description": r.description,
                "confidence_score": r.confidence_score
            }
            for r in relationships
        ]
    
    def get_related_knowledge(
        self,
        knowledge_type: str,
        knowledge_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get all related knowledge for a given item.
        
        Args:
            knowledge_type: Type of knowledge (entity, concept, document)
            knowledge_id: ID of the knowledge item
            user_id: User ID
            
        Returns:
            Dictionary with related entities, concepts, questions, flashcards, etc.
        """
        related = {
            "documents": [],
            "entities": [],
            "concepts": [],
            "relationships": [],
            "questions": [],
            "flashcards": [],
            "topics": []
        }
        
        if knowledge_type == "entity":
            # Get entity
            entity = self.db.query(KnowledgeEntity).filter(
                KnowledgeEntity.id == knowledge_id
            ).first()
            
            if entity:
                # Get relationships involving this entity
                relationships = self.db.query(KnowledgeRelationship).filter(
                    KnowledgeRelationship.source_name == entity.name,
                    KnowledgeRelationship.target_name == entity.name
                ).all()
                related["relationships"] = [
                    {
                        "id": r.id,
                        "source_name": r.source_name,
                        "relationship_type": r.relationship_type,
                        "target_name": r.target_name
                    }
                    for r in relationships
                ]
        
        elif knowledge_type == "concept":
            # Get concept
            concept = self.db.query(KnowledgeConcept).filter(
                KnowledgeConcept.id == knowledge_id
            ).first()
            
            if concept:
                # Get related concepts
                related_concepts = concept.related_concepts or []
                if related_concepts:
                    concepts = self.db.query(KnowledgeConcept).join(Document).filter(
                        Document.owner_id == user_id,
                        KnowledgeConcept.name.in_(related_concepts)
                    ).limit(10).all()
                    
                    related["concepts"] = [
                        {
                            "id": c.id,
                            "name": c.name,
                            "description": c.description
                        }
                        for c in concepts
                    ]
        
        elif knowledge_type == "document":
            # Get document knowledge
            doc = self.db.query(Document).filter(
                Document.id == knowledge_id,
                Document.owner_id == user_id
            ).first()
            
            if doc:
                # Related entities
                entities = self.db.query(KnowledgeEntity).filter(
                    KnowledgeEntity.document_id == knowledge_id
                ).limit(20).all()
                related["entities"] = [
                    {"id": e.id, "name": e.name, "entity_type": e.entity_type}
                    for e in entities
                ]
                
                # Related concepts
                concepts = self.db.query(KnowledgeConcept).filter(
                    KnowledgeConcept.document_id == knowledge_id
                ).limit(20).all()
                related["concepts"] = [
                    {"id": c.id, "name": c.name, "description": c.description}
                    for c in concepts
                ]
                
                # Related topics
                topics = self.db.query(DocumentTopic).filter(
                    DocumentTopic.document_id == knowledge_id
                ).all()
                related["topics"] = [
                    {"id": t.id, "topic_name": t.topic_name, "category": t.category}
                    for t in topics
                ]
                
                # Related flashcards
                flashcards = self.db.query(KnowledgeFlashcard).filter(
                    KnowledgeFlashcard.document_id == knowledge_id
                ).limit(10).all()
                related["flashcards"] = [
                    {"id": f.id, "front": f.front, "back": f.back, "topic": f.topic}
                    for f in flashcards
                ]
                
                # Related questions
                questions = self.db.query(GeneratedQuestion).filter(
                    GeneratedQuestion.document_id == knowledge_id
                ).limit(10).all()
                related["questions"] = [
                    {"id": q.id, "question_text": q.question_text, "difficulty": q.difficulty}
                    for q in questions
                ]
        
        return related
    
    def get_knowledge_graph_preview(
        self,
        document_id: int,
        user_id: int,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Get knowledge graph preview for a document.
        
        Returns nodes and edges for visualization.
        """
        # Verify ownership
        doc = self.db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == user_id
        ).first()
        
        if not doc:
            return {"nodes": [], "edges": []}
        
        # Get entities as nodes
        entities = self.db.query(KnowledgeEntity).filter(
            KnowledgeEntity.document_id == document_id
        ).limit(limit).all()
        
        nodes = []
        edges = []
        node_ids = set()
        
        for entity in entities:
            if entity.id not in node_ids:
                nodes.append({
                    "id": f"entity_{entity.id}",
                    "label": entity.name,
                    "type": "entity",
                    "subtype": entity.entity_type,
                    "weight": entity.mentions
                })
                node_ids.add(entity.id)
        
        # Get relationships as edges
        relationships = self.db.query(KnowledgeRelationship).filter(
            KnowledgeRelationship.document_id == document_id
        ).limit(limit).all()
        
        for rel in relationships:
            edges.append({
                "source": f"concept_{rel.source_id}" if rel.source_type == "concept" else f"entity_{rel.source_id}",
                "target": f"concept_{rel.target_id}" if rel.target_type == "concept" else f"entity_{rel.target_id}",
                "label": rel.relationship_type,
                "weight": rel.confidence_score
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_quality_overview(self, user_id: int) -> Dict[str, Any]:
        """Get quality overview for user's documents."""
        # Get documents with quality scores
        quality_data = self.db.query(
            Document.id,
            Document.title,
            Document.file_path,
            KnowledgeQuality.overall_quality_score,
            KnowledgeQuality.overall_confidence_score,
            KnowledgeQuality.total_entities,
            KnowledgeQuality.total_concepts,
            KnowledgeQuality.total_relationships
        ).outerjoin(
            KnowledgeQuality,
            Document.id == KnowledgeQuality.document_id
        ).filter(
            Document.owner_id == user_id
        ).all()
        
        # Calculate statistics
        scored_docs = [d for d in quality_data if d.overall_quality_score is not None]
        
        avg_quality = sum(d.overall_quality_score for d in scored_docs) / len(scored_docs) if scored_docs else 0
        avg_confidence = sum(d.overall_confidence_score for d in scored_docs) / len(scored_docs) if scored_docs else 0
        
        return {
            "total_documents": len(quality_data),
            "documents_with_quality": len(scored_docs),
            "average_quality_score": round(avg_quality, 2),
            "average_confidence_score": round(avg_confidence, 2),
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "quality_score": d.overall_quality_score,
                    "confidence_score": d.overall_confidence_score,
                    "entity_count": d.total_entities or 0,
                    "concept_count": d.total_concepts or 0,
                    "relationship_count": d.total_relationships or 0
                }
                for d in quality_data[:20]
            ]
        }
    
    def get_dashboard_stats(self, user_id: int) -> Dict[str, Any]:
        """Get dashboard statistics."""
        # Document counts
        total_docs = self.db.query(Document).filter(
            Document.owner_id == user_id
        ).count()
        
        # Knowledge counts
        entity_count = self.db.query(KnowledgeEntity).join(Document).filter(
            Document.owner_id == user_id
        ).count()
        
        concept_count = self.db.query(KnowledgeConcept).join(Document).filter(
            Document.owner_id == user_id
        ).count()
        
        relationship_count = self.db.query(KnowledgeRelationship).join(Document).filter(
            Document.owner_id == user_id
        ).count()
        
        flashcard_count = self.db.query(KnowledgeFlashcard).join(Document).filter(
            Document.owner_id == user_id
        ).count()
        
        question_count = self.db.query(GeneratedQuestion).join(Document).filter(
            Document.owner_id == user_id
        ).count()
        
        # Note count
        note_count = self.db.query(KnowledgeNote).filter(
            KnowledgeNote.user_id == user_id
        ).count()
        
        return {
            "total_documents": total_docs,
            "total_entities": entity_count,
            "total_concepts": concept_count,
            "total_relationships": relationship_count,
            "total_flashcards": flashcard_count,
            "total_questions": question_count,
            "total_notes": note_count
        }
