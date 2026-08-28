"""
Honest-scope "personalized learning": a history log of what you've
studied, plus simple heuristic suggestions (documents you haven't touched
yet). No spaced-repetition scheduler, no ML model, no adaptive difficulty
-- see README for what a real version of this would need.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.models.document import Document
from src.models.quiz_attempt import QuizAttempt

router = APIRouter(prefix="/activity", tags=["Activity & Suggestions"])


class ActivityItem(BaseModel):
    id: int
    document_id: int
    document_filename: str | None = None
    mode: str
    score: float | None = None
    total: float | None = None

    model_config = ConfigDict(from_attributes=True)


class SuggestionItem(BaseModel):
    document_id: int
    filename: str
    reason: str


@router.get("/history", response_model=list[ActivityItem])
def my_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    rows = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.id.desc())
        .limit(limit)
        .all()
    )
    return [
        ActivityItem(
            id=r.id, document_id=r.document_id,
            document_filename=r.document.filename if r.document else None,
            mode=r.mode, score=r.score, total=r.total,
        )
        for r in rows
    ]


@router.get("/suggestions", response_model=list[SuggestionItem])
def suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Heuristic, not ML: surfaces documents the user has uploaded but never
    generated any study content for. Ordered by upload recency.
    """
    my_documents = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.id.desc())
        .all()
    )

    studied_document_ids = {
        row[0] for row in
        db.query(QuizAttempt.document_id)
        .filter(QuizAttempt.user_id == current_user.id)
        .distinct()
        .all()
    }

    results = []
    for doc in my_documents:
        if doc.id not in studied_document_ids:
            results.append(SuggestionItem(
                document_id=doc.id, filename=doc.filename,
                reason="You haven't generated any study material for this yet.",
            ))

    return results[:10]
