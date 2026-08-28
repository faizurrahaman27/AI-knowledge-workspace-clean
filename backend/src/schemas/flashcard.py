from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class FlashcardGenerateRequest(BaseModel):
    document_id: int
    count: int = 10

    @field_validator("count")
    @classmethod
    def reasonable_count(cls, v: int) -> int:
        if not (1 <= v <= 30):
            raise ValueError("count must be between 1 and 30")
        return v


class FlashcardResponse(BaseModel):
    id: int
    document_id: int
    front: str
    back: str
    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: datetime
    total_reviews: int

    model_config = ConfigDict(from_attributes=True)


class FlashcardReviewRequest(BaseModel):
    grade: str

    @field_validator("grade")
    @classmethod
    def valid_grade(cls, v: str) -> str:
        if v not in ("again", "hard", "good", "easy"):
            raise ValueError("grade must be one of: again, hard, good, easy")
        return v
