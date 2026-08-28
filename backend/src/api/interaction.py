"""
Knowledge Interaction API

REST API for AI Notebook, Collections, Explorer, and Search.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.knowledge.interaction.notebook_service import NotebookService
from src.knowledge.interaction.collection_service import CollectionService
from src.knowledge.interaction.explorer_service import KnowledgeExplorerService
from src.knowledge.interaction.search_service import SemanticSearchService
from src.knowledge.interaction.activity_service import RecentActivityService

router = APIRouter(prefix="/knowledge/interaction", tags=["Knowledge Interaction"])


# ============================================================================
# Notebook Endpoints
# ============================================================================

@router.post("/notes")
async def create_note(
    content: str,
    title: Optional[str] = None,
    note_type: str = "user",
    workspace_id: Optional[int] = None,
    source_document_id: Optional[int] = None,
    source_concept_id: Optional[int] = None,
    source_question_id: Optional[int] = None,
    source_flashcard_id: Optional[int] = None,
    citations: Optional[List[dict]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new note."""
    service = NotebookService(db)
    
    note = service.create_note(
        user_id=current_user.id,
        content=content,
        title=title,
        note_type=note_type,
        workspace_id=workspace_id,
        source_document_id=source_document_id,
        source_concept_id=source_concept_id,
        source_question_id=source_question_id,
        source_flashcard_id=source_flashcard_id,
        citations=citations
    )
    
    return {"id": note.id, "created_at": note.created_at}


@router.get("/notes")
async def get_notes(
    workspace_id: Optional[int] = None,
    note_type: Optional[str] = None,
    pinned_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's notes."""
    service = NotebookService(db)
    
    notes = service.get_notes(
        user_id=current_user.id,
        workspace_id=workspace_id,
        note_type=note_type,
        pinned_only=pinned_only,
        limit=limit,
        offset=offset
    )
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "note_type": n.note_type,
            "is_pinned": n.is_pinned,
            "citations": n.citations,
            "ai_generated": n.ai_generated,
            "created_at": n.created_at,
            "updated_at": n.updated_at
        }
        for n in notes
    ]


@router.get("/notes/{note_id}")
async def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific note."""
    service = NotebookService(db)
    
    note = service.get_note(note_id, current_user.id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "note_type": note.note_type,
        "is_pinned": note.is_pinned,
        "citations": note.citations,
        "ai_generated": note.ai_generated,
        "ai_model": note.ai_model,
        "source_document_id": note.source_document_id,
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }


@router.put("/notes/{note_id}")
async def update_note(
    note_id: int,
    content: Optional[str] = None,
    title: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a note."""
    service = NotebookService(db)
    
    note = service.update_note(
        note_id=note_id,
        user_id=current_user.id,
        content=content,
        title=title
    )
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"id": note.id, "updated_at": note.updated_at}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a note."""
    service = NotebookService(db)
    
    if not service.delete_note(note_id, current_user.id):
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"status": "deleted"}


@router.post("/notes/{note_id}/pin")
async def pin_note(
    note_id: int,
    pinned: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pin or unpin a note."""
    service = NotebookService(db)
    
    note = service.pin_note(note_id, current_user.id, pinned)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"id": note.id, "is_pinned": note.is_pinned}


# ============================================================================
# Collection Endpoints
# ============================================================================

@router.post("/collections")
async def create_collection(
    name: str,
    description: Optional[str] = None,
    collection_type: str = "folder",
    parent_id: Optional[int] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new collection."""
    service = CollectionService(db)
    
    collection = service.create_collection(
        user_id=current_user.id,
        name=name,
        description=description,
        collection_type=collection_type,
        parent_id=parent_id,
        color=color,
        icon=icon,
        tags=tags
    )
    
    return {"id": collection.id, "created_at": collection.created_at}


@router.get("/collections")
async def get_collections(
    parent_id: Optional[int] = None,
    collection_type: Optional[str] = None,
    favorites_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's collections."""
    service = CollectionService(db)
    
    collections = service.get_collections(
        user_id=current_user.id,
        parent_id=parent_id,
        collection_type=collection_type,
        favorites_only=favorites_only,
        limit=limit,
        offset=offset
    )
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "collection_type": c.collection_type,
            "parent_id": c.parent_id,
            "color": c.color,
            "icon": c.icon,
            "tags": c.tags,
            "is_favorite": c.is_favorite,
            "item_count": len(c.items),
            "created_at": c.created_at
        }
        for c in collections
    ]


@router.get("/collections/tree")
async def get_collection_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get collection tree structure."""
    service = CollectionService(db)
    
    return service.get_collection_tree(current_user.id)


@router.post("/collections/{collection_id}/items")
async def add_collection_item(
    collection_id: int,
    item_type: str,
    item_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an item to a collection."""
    service = CollectionService(db)
    
    item = service.add_item_to_collection(
        collection_id=collection_id,
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
        notes=notes
    )
    
    if not item:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return {"id": item.id}


@router.get("/collections/{collection_id}/items")
async def get_collection_items(
    collection_id: int,
    item_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get items in a collection."""
    service = CollectionService(db)
    
    items = service.get_collection_items(
        collection_id=collection_id,
        user_id=current_user.id,
        item_type=item_type,
        limit=limit,
        offset=offset
    )
    
    return [
        {
            "id": i.id,
            "item_type": i.item_type,
            "item_id": i.item_id,
            "order_index": i.order_index,
            "notes": i.notes,
            "created_at": i.created_at
        }
        for i in items
    ]


@router.delete("/collections/{collection_id}/items/{item_type}/{item_id}")
async def remove_collection_item(
    collection_id: int,
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an item from a collection."""
    service = CollectionService(db)
    
    if not service.remove_item_from_collection(
        collection_id, item_type, item_id, current_user.id
    ):
        raise HTTPException(status_code=404, detail="Collection or item not found")
    
    return {"status": "removed"}


# ============================================================================
# Explorer Endpoints
# ============================================================================

@router.get("/explorer/topics")
async def get_topics_overview(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get topics overview."""
    service = KnowledgeExplorerService(db)
    
    return service.get_topics_overview(current_user.id, limit)


@router.get("/explorer/entities")
async def get_entities_by_type(
    entity_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get entities by type."""
    service = KnowledgeExplorerService(db)
    
    return service.get_entities_by_type(current_user.id, entity_type, limit)


@router.get("/explorer/entity-types")
async def get_entity_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all entity types."""
    service = KnowledgeExplorerService(db)
    
    return service.get_entity_types(current_user.id)


@router.get("/explorer/relationships")
async def get_relationships(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get relationships overview."""
    service = KnowledgeExplorerService(db)
    
    return service.get_relationships_overview(current_user.id, limit)


@router.get("/explorer/related/{knowledge_type}/{knowledge_id}")
async def get_related_knowledge(
    knowledge_type: str,
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get related knowledge for an item."""
    service = KnowledgeExplorerService(db)
    
    return service.get_related_knowledge(knowledge_type, knowledge_id, current_user.id)


@router.get("/explorer/graph/{document_id}")
async def get_knowledge_graph_preview(
    document_id: int,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge graph preview for a document."""
    service = KnowledgeExplorerService(db)
    
    return service.get_knowledge_graph_preview(document_id, current_user.id, limit)


@router.get("/explorer/quality")
async def get_quality_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get quality overview."""
    service = KnowledgeExplorerService(db)
    
    return service.get_quality_overview(current_user.id)


@router.get("/explorer/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics."""
    service = KnowledgeExplorerService(db)
    
    return service.get_dashboard_stats(current_user.id)


# ============================================================================
# Search Endpoints
# ============================================================================

@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1),
    types: Optional[str] = Query(None, description="Comma-separated types"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search across all knowledge types."""
    service = SemanticSearchService(db)
    
    search_types = types.split(",") if types else None
    
    return service.search(current_user.id, q, search_types, limit)


@router.get("/search/unified")
async def unified_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unified search across all types."""
    service = SemanticSearchService(db)
    
    return service.unified_search(current_user.id, q, limit)


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get search suggestions."""
    service = SemanticSearchService(db)
    
    return service.get_search_suggestions(current_user.id, q, limit)


# ============================================================================
# Activity Endpoints
# ============================================================================

@router.get("/activity/recent")
async def get_recent_activity(
    activity_type: Optional[str] = None,
    item_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent activity."""
    service = RecentActivityService(db)
    
    return service.get_recent_activity(
        current_user.id, activity_type, item_type, hours, limit
    )


@router.get("/activity/dashboard")
async def get_dashboard(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard data."""
    service = RecentActivityService(db)
    
    return service.get_dashboard_data(current_user.id, limit)


@router.get("/activity/pins")
async def get_pinned_items(
    item_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pinned items."""
    service = RecentActivityService(db)
    
    return service.get_pinned_items(current_user.id, item_type, limit=limit)


@router.post("/activity/pins")
async def pin_item(
    item_type: str,
    item_id: int,
    title: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pin an item."""
    service = RecentActivityService(db)
    
    pinned = service.pin_item(current_user.id, item_type, item_id, title)
    
    return {"id": pinned.id, "created_at": pinned.created_at}


@router.delete("/activity/pins/{item_type}/{item_id}")
async def unpin_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpin an item."""
    service = RecentActivityService(db)
    
    if not service.unpin_item(current_user.id, item_type, item_id):
        raise HTTPException(status_code=404, detail="Pinned item not found")
    
    return {"status": "unpinned"}


@router.get("/activity/summary")
async def get_activity_summary(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get activity summary."""
    service = RecentActivityService(db)
    
    return service.get_activity_summary(current_user.id, days)
