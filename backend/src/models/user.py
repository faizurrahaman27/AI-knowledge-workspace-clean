from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False, index=True)

    # Nullable so Google-only accounts (no password set) are representable.
    hashed_password = Column(String, nullable=True)

    google_sub = Column(String, unique=True, nullable=True, index=True)

    # RBAC
    role = Column(String, nullable=False, default="customer")

    is_active = Column(Integer, nullable=False, default=1)

    # JWT token version
    token_version = Column(Integer, nullable=False, default=0)

    # Account lockout
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Password reset
    reset_token_hash = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Email verification
    email_verified = Column(Integer, nullable=False, default=0)
    verification_token_hash = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)

    # Two-factor authentication
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Integer, nullable=False, default=0)
    totp_backup_codes_hash = Column(String, nullable=True)

    theme = Column(String, nullable=False, default="dark")

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    documents = relationship(
        "Document",
        back_populates="owner",
    )

    chats = relationship(
        "Chat",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    workspaces = relationship(
        "Workspace",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    collections = relationship(
        "KnowledgeCollection",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    workspace_layouts = relationship(
        "WorkspaceLayout",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def has_password(self) -> bool:
        """True unless this is a Google-only account with no password set."""
        return self.hashed_password is not None