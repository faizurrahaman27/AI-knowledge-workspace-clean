from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from src.db.database import Base


class Annotation(Base):
    """
    A note pinned to a specific spot on a specific page of a document --
    optionally attached to a quoted text selection. Covers both use
    cases from the feature list: "persistent annotations" (a highlighted
    selection + note) and "notes attached to PDF" (a freeform note with
    no selection) are the same model, distinguished by whether
    quote_text is set.

    Honest scope: this stores a normalized (x_percent, y_percent) anchor
    point captured from the text selection's position at render time, not
    a resizable/draggable highlight rectangle -- good enough to place a
    marker in the right spot and reopen the note, not a full annotation
    editor with shapes, drawing, or freehand ink.
    """

    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    page = Column(Integer, nullable=False)

    quote_text = Column(Text, nullable=True)   # the selected/highlighted text, if any
    note_text = Column(Text, nullable=False)   # the user's actual note/comment

    color = Column(String, nullable=False, default="yellow")

    # Normalized position (0.0-1.0) within the rendered page, so a marker
    # can be placed at the right spot regardless of zoom/render scale.
    x_percent = Column(Float, nullable=True)
    y_percent = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document")
    user = relationship("User")
