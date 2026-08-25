"""PullRequest model — GitHub PRs received via webhook.

A PR is a distinct, longer-lived entity from a Commit: it opens, gets
synchronized (new commits pushed) potentially many times, and eventually
merges or closes. Modeling it as its own table (rather than bolting PR
state onto Commit) keeps that lifecycle explicit and lets one row represent
"this PR" across every webhook delivery about it.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class PullRequestState(str, enum.Enum):
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"  # closed without merging


class PullRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pull_requests"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    html_url: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)  # head ref
    base_branch: Mapped[str] = mapped_column(String(255), nullable=False)

    state: Mapped[PullRequestState] = mapped_column(
        SAEnum(PullRequestState, name="pull_request_state", values_callable=lambda obj: [e.value for e in obj]),
        default=PullRequestState.OPEN,
        nullable=False,
    )
    merged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    files_changed: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # same shape as Commit.files_changed

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at_github: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # AI analysis status — mirrors Commit.analyzed; True once analyze_activity
    # has run for this PR's current state (re-set to False on synchronize).
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")  # noqa: F821
    suggestions: Mapped[list["Suggestion"]] = relationship(  # noqa: F821
        "Suggestion", back_populates="pull_request"
    )

    __table_args__ = (
        Index("ix_pull_requests_repository_number", "repository_id", "number", unique=True),
    )
