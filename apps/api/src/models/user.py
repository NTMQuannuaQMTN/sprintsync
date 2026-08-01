"""User model — GitHub OAuth identity."""
from typing import Optional

from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    github_id: Mapped[int] = mapped_column(unique=True, nullable=False, index=True)
    github_username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    github_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    repositories: Mapped[list["Repository"]] = relationship(  # noqa: F821
        "Repository", back_populates="owner", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(  # noqa: F821
        "ActivityLog", back_populates="user"
    )

    __table_args__ = (
        Index("ix_users_github_username", "github_username"),
    )

    def __repr__(self) -> str:
        return f"<User {self.github_username}>"
