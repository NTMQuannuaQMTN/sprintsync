"""WebhookDelivery — generic idempotency record for inbound GitHub webhooks.

GitHub retries a webhook delivery on timeout/5xx using the SAME
X-GitHub-Delivery id. Prior to this, the only dedup in this codebase was
Commit.sha uniqueness — which only protects against re-processing commits
already fully persisted, not against a retried delivery re-running partial
work (e.g. re-creating Suggestions) before the first attempt's commits were
saved, and it does nothing at all for PR events. This table is checked
before ANY event-specific processing: an insert that violates the unique
constraint means "already seen this exact delivery," full stop.
"""
from typing import Optional
import uuid

from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.base import UUIDMixin, TimestampMixin


class WebhookDelivery(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_webhook_deliveries_delivery_id", "delivery_id", unique=True),
    )
