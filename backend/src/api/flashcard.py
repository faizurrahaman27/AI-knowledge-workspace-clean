from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardReviewRequest,
)

from src.services.flashcard_service import (
    generate_and_save_flashcards,
    get_due_flashcards,
    list_flashcards_for_document,
    review_flashcard,
    delete_flashcard,
)

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


@router.post("/generate", response_model=list[FlashcardResponse])
def generate(
    body: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates new flashcards from a document and persists them with
    fresh SM-2 scheduling state (due immediately). Calling this again on
    the same document adds MORE cards -- it doesn't replace existing ones,
    since that would silently wipe someone's review progress."""
    return generate_and_save_flashcards(db, body.document_id, current_user, count=body.count)


@router.get("/due", response_model=list[FlashcardResponse])
def due(
    document_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cards whose due_at has passed -- what the review session should
    show right now. Optionally scoped to one document."""
    return get_due_flashcards(db, current_user, document_id=document_id)


@router.get("/document/{document_id}", response_model=list[FlashcardResponse])
def list_for_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All flashcards for a document, due or not -- e.g. for a "deck
    overview" screen rather than a review session."""
    return list_flashcards_for_document(db, document_id, current_user)


@router.post("/{flashcard_id}/review", response_model=FlashcardResponse)
def review(
    flashcard_id: int,
    body: FlashcardReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits a review grade (again/hard/good/easy) and reschedules the
    card per SM-2 -- see utils/spaced_repetition.py."""
    return review_flashcard(db, flashcard_id, current_user, body.grade)


@router.delete("/{flashcard_id}")
def delete(
    flashcard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_flashcard(db, flashcard_id, current_user)
