from datetime import datetime
import json

from pydantic import BaseModel, ConfigDict, field_validator


class ChatRequest(BaseModel):
    question: str
    document_id: int | None = None
    workspace_id: int | None = None
    explain_level: str | None = None
    want_translation: bool = True


class ChatResponse(BaseModel):
    answer: str


class Citation(BaseModel):
    filename: str | None = None
    page: int | None = None
    chunk: int | None = None
    snippet: str | None = None


class ChatHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    citations: list[Citation] = []
    flagged_reason: str | None = None
    user_id: int | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("citations", mode="before")
    @classmethod
    def parse_citations(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v
