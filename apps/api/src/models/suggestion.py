"""Suggestion model — AI-generated task update proposals."""
import uuid
import enum
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Text, Float, ForeignKey, Enum as SAEnum, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SuggestionAction(str, enum.Enum):
    STATUS_CHANGE = "status_change"
    PROGRESS_UPDATE = "progress_update"
    ADD_COMMENT = "add_comment"


class Suggestion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "suggestions"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    commit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commits.id", ondelete="SET NULL"), nullable=True
    )
    # References auth.users(id) — see models/profile.py for why there's no
    # SQLAlchemy ForeignKey() wrapper on this column.
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    status: Mapped[SuggestionStatus] = mapped_column(
        SAEnum(SuggestionStatus, name="suggestion_status", values_callable=lambda obj: [e.value for e in obj]),
        default=SuggestionStatus.PENDING,
        nullable=False,
    )
    action: Mapped[SuggestionAction] = mapped_column(
        SAEnum(SuggestionAction, name="suggestion_action", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )

    # Proposed change
    proposed_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # new task status
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0.0 – 1.0

    # Supporting evidence
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {files, patterns, reasoning}

    # Review
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="suggestions")  # noqa: F821
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="suggestions")  # noqa: F821
    commit: Mapped[Optional["Commit"]] = relationship("Commit", back_populates="suggestions")  # noqa: F821

    __table_args__ = (
        Index("ix_suggestions_repository_status", "repository_id", "status"),
        Index("ix_suggestions_task_id", "task_id"),
    )
