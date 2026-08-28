from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user

from src.models.user import User
from src.schemas.chat import ChatHistoryItem

from src.services.chat_service import get_chat_history

router = APIRouter(
    prefix="/chat",
    tags=["Chat History"],
)


@router.get("/{document_id}", response_model=list[ChatHistoryItem])
def list_chat_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_chat_history(
        db=db,
        document_id=document_id,
        current_user=current_user,
    )


@router.get("/workspace/{workspace_id}", response_model=list[ChatHistoryItem])
def list_workspace_chat_history(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Shared thread: every workspace member sees the same history."""
    return get_chat_history(
        db=db,
        workspace_id=workspace_id,
        current_user=current_user,
    )
