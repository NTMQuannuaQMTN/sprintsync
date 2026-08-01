"""Repository model — connected GitHub repositories."""
import uuid
from typing import Optional

from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class Repository(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repositories"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # GitHub metadata
    github_repo_id: Mapped[int] = mapped_column(unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)  # owner/repo
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    html_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Webhook
    webhook_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    webhook_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Computed health score (0-100, cached)
    health_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="repositories")  # noqa: F821
    project_specs: Mapped[list["ProjectSpecification"]] = relationship(  # noqa: F821
        "ProjectSpecification", back_populates="repository", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[list["Commit"]] = relationship(  # noqa: F821
        "Commit", back_populates="repository", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(  # noqa: F821
        "Suggestion", back_populates="repository", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(  # noqa: F821
        "ActivityLog", back_populates="repository"
    )

    __table_args__ = (
        Index("ix_repositories_owner_id", "owner_id"),
        Index("ix_repositories_full_name", "full_name"),
    )

    def __repr__(self) -> str:
        return f"<Repository {self.full_name}>"
