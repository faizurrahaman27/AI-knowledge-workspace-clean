from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class AnnotationCreate(BaseModel):
    page: int
    note_text: str
    quote_text: str | None = None
    color: str = "yellow"
    x_percent: float | None = None
    y_percent: float | None = None

    @field_validator("page")
    @classmethod
    def page_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be 1 or greater")
        return v

    @field_validator("note_text")
    @classmethod
    def note_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("note_text cannot be blank")
        return v.strip()


class AnnotationResponse(BaseModel):
    id: int
    document_id: int
    page: int
    quote_text: str | None
    note_text: str
    color: str
    x_percent: float | None
    y_percent: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
