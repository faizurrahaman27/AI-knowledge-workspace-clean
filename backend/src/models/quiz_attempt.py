from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship

from src.db.database import Base


class QuizAttempt(Base):
    """
    Records one quiz/flashcard/study-mode attempt, for a basic personal
    progress view (score over time, weak topics by document). This is
    honest-scope "personalized learning": history + simple aggregates,
    not a spaced-repetition scheduler or ML-based recommendation engine.
    """
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    mode = Column(String, nullable=False)  # "quiz", "flashcards", etc.
    score = Column(Float, nullable=True)  # correct count
    total = Column(Float, nullable=True)  # total questions

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    user = relationship("User")
    document = relationship("Document")
