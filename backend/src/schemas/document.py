from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):

    id: int

    filename: str

    content_type: str | None = None

    size_bytes: int | None = None

    language_code: str | None = None

    language_name: str | None = None

    created_at: datetime | None = None

    source_url: str | None = None

    # Note: file_path is intentionally NOT exposed here.
    # It's a server-local filesystem path and leaking it to clients
    # has no benefit and a small information-disclosure cost.

    model_config = ConfigDict(from_attributes=True)
