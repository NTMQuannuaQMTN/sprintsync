"""ActivityLog model — audit trail of all system events."""
import uuid
import enum
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class ActivityType(str, enum.Enum):
    REPO_CONNECTED = "repo_connected"
    SPEC_UPLOADED = "spec_uploaded"
    TASKS_GENERATED = "tasks_generated"
    COMMIT_RECEIVED = "commit_received"
    SUGGESTION_CREATED = "suggestion_created"
    SUGGESTION_APPROVED = "suggestion_approved"
    SUGGESTION_REJECTED = "suggestion_rejected"
    TASK_UPDATED = "task_updated"
    WEBHOOK_INSTALLED = "webhook_installed"


class ActivityLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "activity_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True
    )

    event_type: Mapped[ActivityType] = mapped_column(
        SAEnum(ActivityType, name="activity_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="activity_logs")  # noqa: F821
    repository: Mapped[Optional["Repository"]] = relationship(  # noqa: F821
        "Repository", back_populates="activity_logs"
    )

    __table_args__ = (
        Index("ix_activity_logs_repository_id", "repository_id"),
        Index("ix_activity_logs_created_at", "created_at"),
    )
