"""
Knowledge API

REST API for accessing extracted knowledge from documents.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.models.document import Document

from src.knowledge.models import (
    DocumentSummary, KnowledgeEntity, KnowledgeConcept,
    KnowledgeRelationship, GeneratedQuestion, KnowledgeFlashcard,
    DocumentTopic, SemanticTag, DocumentSection, KnowledgeMetadata
)

from src.knowledge.processing.pipeline import run_knowledge_extraction

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


# === Knowledge Retrieval Routes ===

@router.get("/{document_id}/summary")
async def get_document_summary(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document summary (all levels)."""
    document = _get_owned_document(db, document_id, current_user)
    
    if not document.summary:
        raise HTTPException(status_code=404, detail="Summary not available")
    
    return {
        "one_sentence_summary": document.summary.one_sentence_summary,
        "executive_summary": document.summary.executive_summary,
        "bullet_summary": document.summary.bullet_summary,
        "detailed_summary": document.summary.detailed_summary,
    }


@router.get("/{document_id}/entities")
async def get_document_entities(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get extracted entities from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    query = db.query(KnowledgeEntity).filter(
        KnowledgeEntity.document_id == document_id
    )
    
    if entity_type:
        query = query.filter(KnowledgeEntity.entity_type == entity_type)
    
    entities = query.order_by(
        KnowledgeEntity.confidence_score.desc(),
        KnowledgeEntity.mentions.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": e.id,
            "name": e.name,
            "entity_type": e.entity_type,
            "description": e.description,
            "mentions": e.mentions,
            "confidence_score": e.confidence_score,
        }
        for e in entities
    ]


@router.get("/{document_id}/concepts")
async def get_document_concepts(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(30, ge=1, le=100),
):
    """Get extracted concepts from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    concepts = db.query(KnowledgeConcept).filter(
        KnowledgeConcept.document_id == document_id
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
            "related_concepts": c.related_concepts or [],
            "confidence_score": c.confidence_score,
        }
        for c in concepts
    ]


@router.get("/{document_id}/relationships")
async def get_document_relationships(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    relationship_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Get extracted relationships from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    query = db.query(KnowledgeRelationship).filter(
        KnowledgeRelationship.document_id == document_id
    )
    
    if relationship_type:
        query = query.filter(
            KnowledgeRelationship.relationship_type == relationship_type
        )
    
    relationships = query.order_by(
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
            "evidence": r.evidence,
            "confidence_score": r.confidence_score,
        }
        for r in relationships
    ]


@router.get("/{document_id}/questions")
async def get_document_questions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    difficulty: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """Get generated questions from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    query = db.query(GeneratedQuestion).filter(
        GeneratedQuestion.document_id == document_id
    )
    
    if difficulty:
        query = query.filter(GeneratedQuestion.difficulty == difficulty)
    if question_type:
        query = query.filter(GeneratedQuestion.question_type == question_type)
    
    questions = query.limit(limit).all()
    
    return [
        {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "answer": q.answer,
            "options": q.options,
            "correct_option_index": q.correct_option_index,
            "topic": q.topic,
        }
        for q in questions
    ]


@router.get("/{document_id}/flashcards")
async def get_document_flashcards(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    difficulty: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """Get generated flashcards from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    query = db.query(KnowledgeFlashcard).filter(
        KnowledgeFlashcard.document_id == document_id
    )
    
    if difficulty:
        query = query.filter(KnowledgeFlashcard.difficulty == difficulty)
    if topic:
        query = query.filter(KnowledgeFlashcard.topic == topic)
    
    flashcards = query.limit(limit).all()
    
    return [
        {
            "id": f.id,
            "front": f.front,
            "back": f.back,
            "topic": f.topic,
            "tags": f.tags or [],
            "difficulty": f.difficulty,
        }
        for f in flashcards
    ]


@router.get("/{document_id}/topics")
async def get_document_topics(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get classified topics from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    topics = db.query(DocumentTopic).filter(
        DocumentTopic.document_id == document_id
    ).order_by(
        DocumentTopic.importance_score.desc()
    ).all()
    
    return [
        {
            "id": t.id,
            "topic_name": t.topic_name,
            "topic_type": t.topic_type,
            "category": t.category,
            "subcategory": t.subcategory,
            "hierarchy_path": t.hierarchy_path or [],
            "prerequisite_topics": t.prerequisite_topics or [],
            "related_topics": t.related_topics or [],
            "confidence_score": t.confidence_score,
            "importance_score": t.importance_score,
        }
        for t in topics
    ]


@router.get("/{document_id}/tags")
async def get_document_tags(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = Query(None),
):
    """Get semantic tags from document."""
    document = _get_owned_document(db, document_id, current_user)
    
    query = db.query(SemanticTag).filter(
        SemanticTag.document_id == document_id
    )
    
    if category:
        query = query.filter(SemanticTag.tag_category == category)
    
    tags = query.order_by(
        SemanticTag.relevance_score.desc()
    ).all()
    
    return [
        {
            "id": t.id,
            "tag": t.tag,
            "tag_category": t.tag_category,
            "context": t.context,
            "relevance_score": t.relevance_score,
        }
        for t in tags
    ]


@router.get("/{document_id}/metadata")
async def get_document_knowledge_metadata(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge extraction metadata for document."""
    document = _get_owned_document(db, document_id, current_user)
    
    if not document.knowledge_metadata:
        raise HTTPException(status_code=404, detail="Knowledge metadata not available")
    
    m = document.knowledge_metadata
    
    return {
        "word_count": m.word_count,
        "sentence_count": m.sentence_count,
        "reading_time_minutes": m.reading_time_minutes,
        "difficulty_score": m.difficulty_score,
        "document_category": m.document_category,
        "academic_subject": m.academic_subject,
        "language": m.language,
        "language_name": m.language_name,
        "entity_count": m.entity_count,
        "concept_count": m.concept_count,
        "relationship_count": m.relationship_count,
        "question_count": m.question_count,
        "flashcard_count": m.flashcard_count,
        "extraction_complete": m.extraction_complete,
    }


# === Knowledge Extraction Routes ===

@router.post("/{document_id}/extract")
async def trigger_knowledge_extraction(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger knowledge extraction for a document.
    
    This starts the async extraction pipeline.
    """
    document = _get_owned_document(db, document_id, current_user)
    
    if document.knowledge_extracted == 1:
        raise HTTPException(
            status_code=409,
            detail="Knowledge extraction already in progress"
        )
    
    if document.knowledge_extracted == 2:
        raise HTTPException(
            status_code=409,
            detail="Knowledge already extracted for this document"
        )
    
    # Trigger extraction (in a real implementation, this would be async)
    try:
        await run_knowledge_extraction(db, document_id)
        return {"status": "completed", "document_id": document_id}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@router.get("/{document_id}/extraction-status")
async def get_extraction_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the status of knowledge extraction for a document."""
    document = _get_owned_document(db, document_id, current_user)
    
    status_map = {
        0: "not_started",
        1: "in_progress",
        2: "completed"
    }
    
    return {
        "document_id": document_id,
        "status": status_map.get(document.knowledge_extracted, "unknown"),
        "error": document.extraction_error,
    }


# === Search Routes ===

@router.get("/search/concepts")
async def search_concepts(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50),
):
    """Search for concepts across user's documents."""
    concepts = db.query(KnowledgeConcept).join(Document).filter(
        Document.owner_id == current_user.id,
        KnowledgeConcept.name.ilike(f"%{q}%")
    ).limit(limit).all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "document_id": c.document_id,
        }
        for c in concepts
    ]


@router.get("/search/entities")
async def search_entities(
    q: str = Query(..., min_length=2),
    entity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50),
):
    """Search for entities across user's documents."""
    query = db.query(KnowledgeEntity).join(Document).filter(
        Document.owner_id == current_user.id,
        KnowledgeEntity.name.ilike(f"%{q}%")
    )
    
    if entity_type:
        query = query.filter(KnowledgeEntity.entity_type == entity_type)
    
    entities = query.limit(limit).all()
    
    return [
        {
            "id": e.id,
            "name": e.name,
            "entity_type": e.entity_type,
            "description": e.description,
            "document_id": e.document_id,
        }
        for e in entities
    ]


# === Helper Functions ===

def _get_owned_document(db: Session, document_id: int, user: User) -> Document:
    """Get document that user owns."""
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == user.id,
        )
        .first()
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document
