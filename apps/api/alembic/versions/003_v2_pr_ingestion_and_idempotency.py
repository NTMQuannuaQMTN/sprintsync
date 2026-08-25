"""V2: pull_requests, webhook_deliveries, suggestion.pull_request_id,
repository.status_mapping

Adds PR-event ingestion (a PR is a distinct, longer-lived entity from a
Commit — its own table, not bolted onto Commit) and generic webhook
idempotency (previously the only dedup was Commit.sha uniqueness, which
does nothing for PR events and doesn't protect a retried delivery from
re-running partial work before commits were persisted).

Revision ID: 003
Revises: 002
Create Date: 2026-08-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE pull_request_state AS ENUM ('open', 'merged', 'closed')"
    )

    op.create_table(
        "pull_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("html_url", sa.Text, nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("base_branch", sa.String(255), nullable=False),
        sa.Column("state", postgresql.ENUM("open", "merged", "closed", name="pull_request_state", create_type=False), server_default="open", nullable=False),
        sa.Column("merged", sa.Boolean, server_default="false", nullable=False),
        sa.Column("additions", sa.Integer, server_default="0"),
        sa.Column("deletions", sa.Integer, server_default="0"),
        sa.Column("changed_files", sa.Integer, server_default="0"),
        sa.Column("files_changed", postgresql.JSONB, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_github", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analyzed", sa.Boolean, server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pull_requests_repository_id", "pull_requests", ["repository_id"])
    op.create_index("ix_pull_requests_repository_number", "pull_requests", ["repository_id", "number"], unique=True)

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("delivery_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhook_deliveries_delivery_id", "webhook_deliveries", ["delivery_id"], unique=True)
    op.create_index("ix_webhook_deliveries_repository_id", "webhook_deliveries", ["repository_id"])

    op.add_column(
        "suggestions",
        sa.Column("pull_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pull_requests.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "repositories",
        sa.Column("status_mapping", postgresql.JSONB, nullable=True),
    )

    # RLS — same pattern as every other table (backend bypasses via
    # service_role; these protect direct PostgREST/supabase-js access).
    op.execute("ALTER TABLE public.pull_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.webhook_deliveries ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY pull_requests_via_repository_owner ON public.pull_requests
        FOR ALL USING (
          repository_id IN (SELECT id FROM public.repositories WHERE owner_id = auth.uid())
        ) WITH CHECK (
          repository_id IN (SELECT id FROM public.repositories WHERE owner_id = auth.uid())
        );
        """
    )
    op.execute(
        """
        CREATE POLICY webhook_deliveries_via_repository_owner ON public.webhook_deliveries
        FOR ALL USING (
          repository_id IN (SELECT id FROM public.repositories WHERE owner_id = auth.uid())
        ) WITH CHECK (
          repository_id IN (SELECT id FROM public.repositories WHERE owner_id = auth.uid())
        );
        """
    )


def downgrade() -> None:
    op.drop_column("repositories", "status_mapping")
    op.drop_column("suggestions", "pull_request_id")
    op.drop_table("webhook_deliveries")
    op.drop_table("pull_requests")
    op.execute("DROP TYPE pull_request_state")
