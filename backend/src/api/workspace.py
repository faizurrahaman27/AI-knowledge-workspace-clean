"""
Workspace API

REST API for workspace management, knowledge source organization,
and workspace-based chat and search functionality.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.team import AssignDocumentRequest
from src.schemas.document import DocumentResponse
from src.services import workspace_service as ws


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# === Request/Response Schemas ===

class WorkspaceCreateRequest(BaseModel):
    """Request to create a workspace."""
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    team_id: Optional[int] = None


class WorkspaceUpdateRequest(BaseModel):
    """Request to update a workspace."""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class TagRequest(BaseModel):
    """Request to add/remove a tag."""
    tag: str


class SearchRequest(BaseModel):
    """Request to search workspaces."""
    query: str
    include_archived: bool = False


# === Workspace CRUD Routes ===

@router.post("/", response_model=dict)
async def create_workspace_api(
    body: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workspace."""
    workspace = ws.create_workspace(
        db=db,
        name=body.name,
        user=current_user,
        description=body.description,
        tags=body.tags,
        color=body.color,
        icon=body.icon,
        team_id=body.team_id
    )
    return workspace.to_summary()


@router.get("/", response_model=List[dict])
async def list_workspaces_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status: active, archived"),
    favorites: bool = Query(False, description="Only show favorites"),
    include_team: bool = Query(True, description="Include team workspaces"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List user's workspaces with optional filters."""
    return ws.list_my_workspaces(
        db=db,
        user=current_user,
        status_filter=status,
        favorites_only=favorites,
        include_team=include_team,
        limit=limit,
        offset=offset
    )


@router.get("/recent", response_model=List[dict])
async def list_recent_workspaces_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
):
    """List recently accessed workspaces."""
    return ws.list_recent_workspaces(db=db, user=current_user, limit=limit)


@router.get("/search", response_model=List[dict])
async def search_workspaces_api(
    q: str = Query(..., min_length=1, description="Search query"),
    include_archived: bool = Query(False, description="Include archived workspaces"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search workspaces by name, description, or tags."""
    return ws.search_workspaces(
        db=db,
        user=current_user,
        query=q,
        include_archived=include_archived
    )


@router.get("/default", response_model=dict)
async def get_default_workspace_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get or create user's default workspace."""
    workspace = ws.get_default_workspace(db=db, user=current_user)
    return workspace.to_summary()


@router.get("/{workspace_id}", response_model=dict)
async def get_workspace_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get workspace details."""
    return ws.get_workspace_detail(db=db, workspace_id=workspace_id, user=current_user)


@router.patch("/{workspace_id}", response_model=dict)
async def update_workspace_api(
    workspace_id: int,
    body: WorkspaceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update workspace properties."""
    workspace = ws.update_workspace(
        db=db,
        workspace_id=workspace_id,
        user=current_user,
        name=body.name,
        description=body.description,
        tags=body.tags,
        color=body.color,
        icon=body.icon
    )
    return workspace.to_summary()


@router.delete("/{workspace_id}")
async def delete_workspace_api(
    workspace_id: int,
    permanent: bool = Query(False, description="Permanently delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a workspace (soft delete by default)."""
    return ws.delete_workspace(
        db=db,
        workspace_id=workspace_id,
        user=current_user,
        permanent=permanent
    )


# === Archive/Restore Routes ===

@router.post("/{workspace_id}/archive", response_model=dict)
async def archive_workspace_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a workspace."""
    workspace = ws.archive_workspace(db=db, workspace_id=workspace_id, user=current_user)
    return workspace.to_summary()


@router.post("/{workspace_id}/restore", response_model=dict)
async def restore_workspace_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore an archived workspace."""
    workspace = ws.restore_workspace(db=db, workspace_id=workspace_id, user=current_user)
    return workspace.to_summary()


@router.post("/{workspace_id}/favorite", response_model=dict)
async def toggle_favorite_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle workspace favorite status."""
    return ws.toggle_favorite_workspace(db=db, workspace_id=workspace_id, user=current_user)


# === Tag Management Routes ===

@router.post("/{workspace_id}/tags", response_model=dict)
async def add_tag_api(
    workspace_id: int,
    body: TagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a tag to workspace."""
    workspace = ws.add_tag_to_workspace(
        db=db,
        workspace_id=workspace_id,
        user=current_user,
        tag=body.tag
    )
    return workspace.to_summary()


@router.delete("/{workspace_id}/tags/{tag}")
async def remove_tag_api(
    workspace_id: int,
    tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a tag from workspace."""
    workspace = ws.remove_tag_from_workspace(
        db=db,
        workspace_id=workspace_id,
        user=current_user,
        tag=tag
    )
    return workspace.to_summary()


# === Document Management Routes ===

@router.post("/{workspace_id}/documents")
async def add_document_api(
    workspace_id: int,
    body: AssignDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a document to workspace."""
    return ws.assign_document(db=db, workspace_id=workspace_id, document_id=body.document_id, user=current_user)


@router.delete("/{workspace_id}/documents/{document_id}")
async def remove_document_api(
    workspace_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a document from workspace."""
    return ws.remove_document(db=db, workspace_id=workspace_id, document_id=document_id, user=current_user)


@router.get("/{workspace_id}/documents", response_model=List[DocumentResponse])
async def list_documents_api(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents in a workspace."""
    return ws.list_workspace_documents(db=db, workspace_id=workspace_id, user=current_user)
