from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.models.quiz_attempt import QuizAttempt
from src.services.document_service import get_owned_document

from src.utils.vector_store import get_document_chunks_sample
from src.utils.llm import generate_study_content, STUDY_MODE_PROMPTS

router = APIRouter(prefix="/study", tags=["Study Mode"])


class StudyRequest(BaseModel):
    document_id: int
    mode: str  # one of STUDY_MODE_PROMPTS keys


class StudyResponse(BaseModel):
    mode: str
    content: str


@router.get("/modes")
def list_modes():
    return {"modes": list(STUDY_MODE_PROMPTS.keys())}


@router.post("/", response_model=StudyResponse)
def generate_study(
    request: StudyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.mode not in STUDY_MODE_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mode '{request.mode}'. Valid: {list(STUDY_MODE_PROMPTS.keys())}",
        )

    # Ownership check (raises 404 if not the owner / doesn't exist).
    get_owned_document(db, request.document_id, current_user)

    chunks, metadatas = get_document_chunks_sample(request.document_id, max_chunks=40)

    if not chunks:
        raise HTTPException(status_code=422, detail="This document has no processed content yet.")

    context = "\n\n".join(
        f"[Page {m.get('page')}] {c}" for c, m in zip(chunks, metadatas)
    )

    content = generate_study_content(context=context, mode=request.mode)

    # Activity log for the "basic personalized learning" suggestions
    # feature -- no score yet since this endpoint doesn't grade anything
    # (the generated quiz text isn't interactive/graded). See
    # api/activity.py and README for exactly what this does and doesn't do.
    db.add(QuizAttempt(
        user_id=current_user.id, document_id=request.document_id,
        mode=request.mode, score=None, total=None,
    ))
    db.commit()

    return StudyResponse(mode=request.mode, content=content)
