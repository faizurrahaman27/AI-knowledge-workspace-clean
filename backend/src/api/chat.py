from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user

from src.models.user import User

from src.schemas.chat import ChatRequest

from src.services.chat_service import chat

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/")
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        chat(
            db=db,
            question=request.question,
            document_id=request.document_id,
            workspace_id=request.workspace_id,
            current_user=current_user,
            explain_level=request.explain_level,
            want_translation=request.want_translation,
        ),
        media_type="application/x-ndjson",
    )
