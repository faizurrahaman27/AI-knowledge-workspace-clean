import json
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.flashcard import Flashcard
from src.models.user import User
from src.services.document_service import get_owned_document
from src.utils.vector_store import get_document_chunks_sample
from src.utils.llm import generate_flashcards_structured
from src.utils.spaced_repetition import schedule_next_review
from src.core.logging import logger


def _extract_json_array(raw: str) -> list:
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("No JSON array found in model output.")


def generate_and_save_flashcards(db: Session, document_id: int, current_user: User, count: int = 10):
    document = get_owned_document(db, document_id, current_user)

    chunks, metadatas = get_document_chunks_sample(document_id, max_chunks=30)
    if not chunks:
        raise HTTPException(status_code=422, detail="This document has no processed content yet.")

    context = "\n\n".join(f"[Page {m.get('page')}] {c}" for c, m in zip(chunks, metadatas))

    raw = generate_flashcards_structured(context=context, count=count)

    try:
        cards_data = _extract_json_array(raw)
    except (ValueError, json.JSONDecodeError):
        logger.warning("Flashcard JSON parse failed for document_id=%s", document_id)
        raise HTTPException(
            status_code=502,
            detail="Could not generate well-formed flashcards this time -- please try again.",
        )

    cards = []
    for item in cards_data:
        if not isinstance(item, dict) or "front" not in item or "back" not in item:
            continue
        card = Flashcard(
            user_id=current_user.id,
            document_id=document.id,
            front=str(item["front"]),
            back=str(item["back"]),
        )
        db.add(card)
        cards.append(card)

    if not cards:
        raise HTTPException(status_code=502, detail="No valid flashcards were generated -- please try again.")

    db.commit()
    for card in cards:
        db.refresh(card)

    logger.info("Generated %d flashcards for document_id=%s user_id=%s", len(cards), document_id, current_user.id)

    return cards


def get_due_flashcards(db: Session, current_user: User, document_id: int | None = None):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    query = db.query(Flashcard).filter(
        Flashcard.user_id == current_user.id,
        Flashcard.due_at <= now,
    )
    if document_id is not None:
        query = query.filter(Flashcard.document_id == document_id)

    return query.order_by(Flashcard.due_at.asc()).all()


def list_flashcards_for_document(db: Session, document_id: int, current_user: User):
    get_owned_document(db, document_id, current_user)  # ownership check, raises 404
    return (
        db.query(Flashcard)
        .filter(Flashcard.user_id == current_user.id, Flashcard.document_id == document_id)
        .order_by(Flashcard.due_at.asc())
        .all()
    )


def review_flashcard(db: Session, flashcard_id: int, current_user: User, grade: str):
    from datetime import datetime, timezone

    card = (
        db.query(Flashcard)
        .filter(Flashcard.id == flashcard_id, Flashcard.user_id == current_user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    try:
        result = schedule_next_review(
            grade=grade,
            ease_factor=card.ease_factor,
            interval_days=card.interval_days,
            repetitions=card.repetitions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    card.ease_factor = result.ease_factor
    card.interval_days = result.interval_days
    card.repetitions = result.repetitions
    card.due_at = result.due_at
    card.last_reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    card.total_reviews += 1

    db.commit()
    db.refresh(card)

    return card


def delete_flashcard(db: Session, flashcard_id: int, current_user: User):
    card = (
        db.query(Flashcard)
        .filter(Flashcard.id == flashcard_id, Flashcard.user_id == current_user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found.")
    db.delete(card)
    db.commit()
    return {"message": "Flashcard deleted."}
