"""Commit model — GitHub commits received via webhook."""
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class Commit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "commits"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    short_sha: Mapped[str] = mapped_column(String(8), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    author_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    html_url: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)

    # Diff stats
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    files_changed: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # [{filename, additions, deletions, patch}]

    # AI analysis status
    analyzed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="commits")  # noqa: F821
    suggestions: Mapped[list["Suggestion"]] = relationship(  # noqa: F821
        "Suggestion", back_populates="commit"
    )

    __table_args__ = (
        Index("ix_commits_repository_sha", "repository_id", "sha", unique=True),
    )
