"""Task model — implementation tasks extracted from project specs."""
import uuid
import enum
from typing import Optional

from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    spec_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_specifications.id", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"), default=TaskStatus.TODO, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, name="task_priority"), default=TaskPriority.MEDIUM, nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # AI-extracted metadata
    ai_tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    ai_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # files, patterns hints

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="tasks")  # noqa: F821
    spec: Mapped[Optional["ProjectSpecification"]] = relationship(  # noqa: F821
        "ProjectSpecification", back_populates="tasks"
    )
    subtasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["Task"]] = relationship("Task", back_populates="subtasks", remote_side="Task.id")
    suggestions: Mapped[list["Suggestion"]] = relationship(  # noqa: F821
        "Suggestion", back_populates="task"
    )

    __table_args__ = (
        Index("ix_tasks_repository_id", "repository_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_parent_id", "parent_id"),
    )

    def __repr__(self) -> str:
        return f"<Task {self.title[:50]}>"
