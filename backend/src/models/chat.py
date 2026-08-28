from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship

from src.db.database import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)

    question = Column(Text, nullable=False)

    answer = Column(Text, nullable=False)

    # JSON-encoded list of {filename, page, chunk, score} used to answer.
    # Kept for auditability, which matters for regulated-industry deployments.
    citations = Column(Text, nullable=True)

    # Set when the guardrail layer blocked or flagged the turn.
    flagged_reason = Column(String, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Exactly one of these is set: a single-document chat, or a
    # workspace chat (searches every document in the workspace, and is
    # visible to every workspace member -- this is the "collaboration"
    # piece: a shared conversation, not just a shared document).
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    user = relationship("User", back_populates="chats")

    document = relationship("Document")
    workspace = relationship("Workspace")
