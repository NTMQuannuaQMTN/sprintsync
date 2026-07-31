"""ProjectSpecification model — uploaded documents."""
import uuid
import enum
from typing import Optional

from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class SpecStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class ProjectSpecification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_specifications"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)  # application/pdf or docx
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)  # Supabase storage path
    storage_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # public or signed URL

    status: Mapped[SpecStatus] = mapped_column(
        SAEnum(SpecStatus, name="spec_status"), default=SpecStatus.PENDING, nullable=False
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        "Repository", back_populates="project_specs"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="spec"
    )

    __table_args__ = (
        Index("ix_project_specifications_repository_id", "repository_id"),
    )
