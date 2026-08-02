"""Profile model — 1:1 extension of Supabase's auth.users.

Identity itself (email, password/OAuth credentials, sessions) is owned and
managed entirely by Supabase Auth in the `auth` schema, which this app does
not create or migrate — it already exists in any Supabase project. This
table only holds GitHub-specific display data and the GitHub provider
token (needed for calling the GitHub API server-side, since Supabase does
not persist/refresh OAuth provider tokens on our behalf).

Rows are created automatically by the `handle_new_user()` trigger defined
in the initial migration whenever a new auth.users row appears (i.e. on
first GitHub sign-in) — never by application code.
"""
import uuid
from typing import Optional

from sqlalchemy import String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.base import TimestampMixin


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    # Intentionally NOT auto-generated (no UUIDMixin/default=uuid.uuid4):
    # this id must always equal the corresponding auth.users.id. No
    # SQLAlchemy ForeignKey() here on purpose — auth.users is a Supabase-
    # managed table this app never maps as a model, and SQLAlchemy's ORM
    # flush machinery requires FK targets to be resolvable in its own
    # MetaData registry, which auth.users deliberately isn't. The actual DB
    # constraint (REFERENCES auth.users(id) ON DELETE CASCADE) is defined in
    # the Alembic migration directly via raw DDL, where a plain string
    # reference works fine since it doesn't go through ORM mapper
    # resolution.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    github_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_profiles_github_username", "github_username"),
    )

    def __repr__(self) -> str:
        return f"<Profile {self.github_username or self.id}>"
