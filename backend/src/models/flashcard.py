from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.db.database import Base


class Flashcard(Base):
    """
    A single reviewable flashcard with SM-2 (SuperMemo 2) spaced-repetition
    scheduling state. SM-2 is the same algorithm Anki's default scheduler
    is based on: a well-known, well-tested formula, not a novel invention
    here -- see utils/spaced_repetition.py for the actual math and a
    citation.
    """
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)

    # --- SM-2 scheduling state ---
    ease_factor = Column(Float, nullable=False, default=2.5)
    interval_days = Column(Integer, nullable=False, default=0)
    repetitions = Column(Integer, nullable=False, default=0)
    due_at = Column(
        DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    last_reviewed_at = Column(DateTime, nullable=True)
    total_reviews = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    user = relationship("User")
    document = relationship("Document")
