"""Integration model — future integration connections (Notion, Jira, etc.)."""
import uuid
import enum
from typing import Optional

from sqlalchemy import String, Text, Boolean, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class IntegrationType(str, enum.Enum):
    GITHUB = "github"
    NOTION = "notion"
    JIRA = "jira"
    LINEAR = "linear"
    CLICKUP = "clickup"
    CONFLUENCE = "confluence"
    GITLAB = "gitlab"


class Integration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "integrations"

    # References auth.users(id) — see models/profile.py for why there's no
    # SQLAlchemy ForeignKey() wrapper on this column.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    integration_type: Mapped[IntegrationType] = mapped_column(
        SAEnum(IntegrationType, name="integration_type", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    workspace_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    workspace_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # encrypted in production
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_integrations_user_type", "user_id", "integration_type", unique=True),
    )
