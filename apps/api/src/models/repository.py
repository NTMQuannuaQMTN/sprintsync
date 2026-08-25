"""Repository model — connected GitHub repositories."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class Repository(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repositories"

    # References Supabase's auth.users(id) — enforced at the DB level by the
    # Alembic migration's raw DDL, not by a SQLAlchemy ForeignKey() here (see
    # models/profile.py for why). No `owner` relationship; load the owning
    # Profile with a separate query keyed on this id.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
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

    # GitHub Action alternative ingestion path (V2 Phase 8): a per-repo
    # bearer credential the repo owner puts in their own GitHub Actions
    # secrets, so their workflow can POST events to
    # POST /webhook/action without SprintSync ever needing GitHub App/OAuth
    # webhook-install permission on the repo -- useful when the connecting
    # user isn't a repo admin (webhook install requires admin; a repo's own
    # Actions workflow does not). Null until the user generates one via
    # POST /repositories/{id}/action-token. Stored the same way
    # Profile.github_access_token already is (see that model's docstring).
    action_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)

    # Computed health score (0-100, cached)
    health_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Last time _sync_commits_from_github (commits.py) actually hit the
    # GitHub API for this repo — lets that sync skip the round-trip (and
    # the per-new-commit detail fetches) on every single page load, instead
    # of only on a cooldown. See COMMIT_SYNC_COOLDOWN_SECONDS in commits.py.
    last_commit_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # V2: per-repo override for which task status an event maps to (push,
    # pr_opened, pr_merged, ...). Merged over DEFAULT_STATUS_MAPPING
    # (services/status_mapping.py) — an unset key here falls back to the
    # default rather than every repo needing every key. Never destroys a
    # user's own workflow: this only ever supplies AI *suggestions*, which
    # still require human approval before any Task row actually changes.
    status_mapping: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    project_specs: Mapped[list["ProjectSpecification"]] = relationship(  # noqa: F821
        "ProjectSpecification", back_populates="repository", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[list["Commit"]] = relationship(  # noqa: F821
        "Commit", back_populates="repository", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(  # noqa: F821
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
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
