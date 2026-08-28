"""
Workspace Service

Enhanced workspace service with comprehensive CRUD operations, organization features,
and workspace statistics for the AI Knowledge Workspace.
"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from src.models.workspace import Workspace, WorkspaceStatus
from src.models.document import Document
from src.models.chat import Chat
from src.models.user import User
from src.services.team_service import get_membership


def user_can_access_workspace(db: Session, workspace: Workspace, user: User) -> bool:
    """Check if user can access a workspace."""
    if workspace.owner_id is not None:
        return workspace.owner_id == user.id
    if workspace.team_id is not None:
        return get_membership(db, workspace.team_id, user.id) is not None
    return False


def _get_owned_or_member_workspace(
    db: Session, 
    workspace_id: int, 
    user: User,
    include_deleted: bool = False
) -> Workspace:
    """Get workspace by ID with access check."""
    query = db.query(Workspace).filter(Workspace.id == workspace_id)
    
    if not include_deleted:
        query = query.filter(Workspace.status != WorkspaceStatus.DELETED.value)
    
    workspace = query.first()
    
    if not workspace or not user_can_access_workspace(db, workspace, user):
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return workspace


def _update_workspace_statistics(db: Session, workspace: Workspace) -> None:
    """Update workspace statistics based on current state."""
    source_count = db.query(Document).filter(Document.workspace_id == workspace.id).count()
    chat_count = db.query(Chat).filter(Chat.workspace_id == workspace.id).count()
    total_size = db.query(func.coalesce(func.sum(Document.size_bytes), 0)).filter(
        Document.workspace_id == workspace.id
    ).scalar()
    
    workspace.source_count = source_count
    workspace.chat_count = chat_count
    workspace.total_size_bytes = total_size or 0


def create_workspace(
    db: Session,
    name: str,
    user: User,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    team_id: Optional[int] = None
) -> Workspace:
    """
    Create a new workspace.
    
    Args:
        db: Database session
        name: Workspace name
        user: Owner user
        description: Optional description
        tags: Optional list of tags
        color: Optional hex color for UI
        icon: Optional emoji/icon identifier
        team_id: Optional team ID for collaborative workspace
        
    Returns:
        Created workspace
    """
    if team_id is not None:
        if not get_membership(db, team_id, user.id):
            raise HTTPException(status_code=403, detail="You're not a member of that team.")
        workspace = Workspace(
            name=name,
            description=description,
            team_id=team_id,
            owner_id=None,
            tags=tags or [],
            color=color,
            icon=icon,
        )
    else:
        workspace = Workspace(
            name=name,
            description=description,
            owner_id=user.id,
            team_id=None,
            tags=tags or [],
            color=color,
            icon=icon,
        )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def update_workspace(
    db: Session,
    workspace_id: int,
    user: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None
) -> Workspace:
    """
    Update workspace properties.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user: Current user
        name: Optional new name
        description: Optional new description
        tags: Optional new tags
        color: Optional new color
        icon: Optional new icon
        
    Returns:
        Updated workspace
    """
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    
    if name is not None:
        workspace.name = name
    if description is not None:
        workspace.description = description
    if tags is not None:
        workspace.tags = tags
    if color is not None:
        workspace.color = color
    if icon is not None:
        workspace.icon = icon
    
    db.commit()
    db.refresh(workspace)
    return workspace


def delete_workspace(db: Session, workspace_id: int, user: User, permanent: bool = False) -> dict:
    """
    Delete a workspace (soft delete by default).
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user: Current user
        permanent: If True, permanently delete; otherwise soft delete
        
    Returns:
        Success message
    """
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    
    if permanent:
        # Permanent delete - remove all documents' workspace association
        db.query(Document).filter(Document.workspace_id == workspace.id).update(
            {"workspace_id": None}
        )
        db.query(Chat).filter(Chat.workspace_id == workspace.id).update(
            {"workspace_id": None}
        )
        db.delete(workspace)
        db.commit()
        return {"message": "Workspace permanently deleted."}
    else:
        # Soft delete
        workspace.status = WorkspaceStatus.DELETED.value
        db.commit()
        return {"message": "Workspace deleted."}


def archive_workspace(db: Session, workspace_id: int, user: User) -> Workspace:
    """
    Archive a workspace.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user: Current user
        
    Returns:
        Archived workspace
    """
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    workspace.archive()
    db.commit()
    db.refresh(workspace)
    return workspace


def restore_workspace(db: Session, workspace_id: int, user: User) -> Workspace:
    """
    Restore an archived workspace.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user: Current user
        
    Returns:
        Restored workspace
    """
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    
    if not workspace.is_archived:
        raise HTTPException(status_code=400, detail="Workspace is not archived.")
    
    workspace.restore()
    db.commit()
    db.refresh(workspace)
    return workspace


def toggle_favorite_workspace(db: Session, workspace_id: int, user: User) -> dict:
    """
    Toggle workspace favorite status.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user: Current user
        
    Returns:
        New favorite status
    """
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    new_status = workspace.toggle_favorite()
    db.commit()
    return {"is_favorite": new_status}


def list_my_workspaces(
    db: Session,
    user: User,
    status_filter: Optional[str] = None,
    favorites_only: bool = False,
    include_team: bool = True,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """
    List user's workspaces with optional filters.
    
    Args:
        db: Database session
        user: Current user
        status_filter: Filter by status (active, archived)
        favorites_only: Only return favorites
        include_team: Include team workspaces
        limit: Maximum results
        offset: Results offset for pagination
        
    Returns:
        List of workspace summaries
    """
    # Get personal workspaces
    query = db.query(Workspace).filter(
        Workspace.owner_id == user.id,
        Workspace.status != WorkspaceStatus.DELETED.value
    )
    
    if status_filter:
        query = query.filter(Workspace.status == status_filter)
    
    if favorites_only:
        query = query.filter(Workspace.is_favorite == True)
    
    personal = query.order_by(Workspace.updated_at.desc()).all()
    
    workspaces = list(personal)
    
    # Get team workspaces if requested
    if include_team:
        from src.models.team import TeamMembership
        team_ids = [
            m.team_id for m in
            db.query(TeamMembership).filter(TeamMembership.user_id == user.id).all()
        ]
        
        if team_ids:
            team_query = db.query(Workspace).filter(
                Workspace.team_id.in_(team_ids),
                Workspace.status != WorkspaceStatus.DELETED.value
            )
            
            if status_filter:
                team_query = team_query.filter(Workspace.status == status_filter)
            
            if favorites_only:
                team_query = team_query.filter(Workspace.is_favorite == True)
            
            team_workspaces = team_query.order_by(Workspace.updated_at.desc()).all()
            workspaces.extend(team_workspaces)
    
    # Sort by updated time
    workspaces.sort(key=lambda w: w.updated_at or w.created_at, reverse=True)
    
    # Apply pagination
    workspaces = workspaces[offset:offset + limit]
    
    # Build results with statistics
    results = []
    for ws in workspaces:
        _update_workspace_statistics(db, ws)
        results.append(ws.to_summary())
    
    return results


def list_recent_workspaces(db: Session, user: User, limit: int = 10) -> List[dict]:
    """
    List recently accessed workspaces.
    
    Args:
        db: Database session
        user: Current user
        limit: Maximum results
        
    Returns:
        List of recent workspace summaries
    """
    from src.models.team import TeamMembership
    
    # Get user's personal and team workspace IDs
    personal_ids = [w.id for w in db.query(Workspace).filter(
        Workspace.owner_id == user.id,
        Workspace.status != WorkspaceStatus.DELETED.value
    ).all()]
    
    team_ids = [
        m.team_id for m in
        db.query(TeamMembership).filter(TeamMembership.user_id == user.id).all()
    ]
    team_workspace_ids = [w.id for w in db.query(Workspace).filter(
        Workspace.team_id.in_(team_ids),
        Workspace.status != WorkspaceStatus.DELETED.value
    ).all()] if team_ids else []
    
    all_workspace_ids = personal_ids + team_workspace_ids
    
    if not all_workspace_ids:
        return []
    
    # Query by last accessed time
    workspaces = db.query(Workspace).filter(
        Workspace.id.in_(all_workspace_ids)
    ).order_by(
        Workspace.last_accessed_at.desc().nullslast()
    ).limit(limit).all()
    
    results = []
    for ws in workspaces:
        _update_workspace_statistics(db, ws)
        results.append(ws.to_summary())
    
    return results


def get_workspace_detail(db: Session, workspace_id: int, user: User) -> dict:
    """
    Get workspace with full details.
    
    Args:
        db: Database session
        workspace_id: Workspace ID
        user: Current user
        
    Returns:
        Workspace details
    """
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    workspace.update_last_accessed()
    _update_workspace_statistics(db, workspace)
    db.commit()
    return workspace.to_detail()


def add_tag_to_workspace(db: Session, workspace_id: int, user: User, tag: str) -> Workspace:
    """Add a tag to workspace."""
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    workspace.add_tag(tag)
    db.commit()
    db.refresh(workspace)
    return workspace


def remove_tag_from_workspace(db: Session, workspace_id: int, user: User, tag: str) -> Workspace:
    """Remove a tag from workspace."""
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    workspace.remove_tag(tag)
    db.commit()
    db.refresh(workspace)
    return workspace


def search_workspaces(
    db: Session,
    user: User,
    query: str,
    include_archived: bool = False
) -> List[dict]:
    """
    Search workspaces by name, description, or tags.
    
    Args:
        db: Database session
        user: Current user
        query: Search query
        include_archived: Include archived workspaces
        
    Returns:
        List of matching workspaces
    """
    from src.models.team import TeamMembership
    
    query_lower = f"%{query.lower()}%"
    
    # Personal workspaces
    personal = db.query(Workspace).filter(
        Workspace.owner_id == user.id,
        Workspace.status != WorkspaceStatus.DELETED.value,
        or_(
            func.lower(Workspace.name).like(query_lower),
            func.lower(Workspace.description).like(query_lower),
        )
    )
    
    if not include_archived:
        personal = personal.filter(Workspace.status != WorkspaceStatus.ARCHIVED.value)
    
    workspaces = personal.all()
    
    # Team workspaces
    team_ids = [
        m.team_id for m in
        db.query(TeamMembership).filter(TeamMembership.user_id == user.id).all()
    ]
    
    if team_ids:
        team_workspaces = db.query(Workspace).filter(
            Workspace.team_id.in_(team_ids),
            Workspace.status != WorkspaceStatus.DELETED.value,
            or_(
                func.lower(Workspace.name).like(query_lower),
                func.lower(Workspace.description).like(query_lower),
            )
        )
        
        if not include_archived:
            team_workspaces = team_workspaces.filter(Workspace.status != WorkspaceStatus.ARCHIVED.value)
        
        workspaces.extend(team_workspaces.all())
    
    results = []
    for ws in workspaces:
        _update_workspace_statistics(db, ws)
        results.append(ws.to_summary())
    
    return results


def assign_document(db: Session, workspace_id: int, document_id: int, user: User):
    """Assign a document to workspace."""
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)

    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    document.workspace_id = workspace.id
    _update_workspace_statistics(db, workspace)
    db.commit()
    return {"message": f"Added '{document.filename}' to workspace '{workspace.name}'."}


def remove_document(db: Session, workspace_id: int, document_id: int, user: User):
    """Remove a document from workspace."""
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)

    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == workspace.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not in this workspace.")

    document.workspace_id = None
    _update_workspace_statistics(db, workspace)
    db.commit()
    return {"message": "Removed from workspace."}


def get_workspace_document_ids(db: Session, workspace_id: int, user: User) -> list[int]:
    """Get all document IDs in a workspace."""
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    docs = db.query(Document).filter(Document.workspace_id == workspace.id).all()
    return [d.id for d in docs]


def list_workspace_documents(db: Session, workspace_id: int, user: User):
    """List all documents in a workspace."""
    workspace = _get_owned_or_member_workspace(db, workspace_id, user)
    return db.query(Document).filter(Document.workspace_id == workspace.id).all()


def get_default_workspace(db: Session, user: User) -> Optional[Workspace]:
    """
    Get or create user's default workspace.
    
    Args:
        db: Database session
        user: Current user
        
    Returns:
        Default workspace
    """
    # Look for existing "My Workspace" or create one
    workspace = db.query(Workspace).filter(
        Workspace.owner_id == user.id,
        Workspace.name == "My Workspace",
        Workspace.status != WorkspaceStatus.DELETED.value
    ).first()
    
    if not workspace:
        workspace = create_workspace(
            db=db,
            name="My Workspace",
            user=user,
            description="Your default workspace for organizing knowledge sources"
        )
    
    return workspace
