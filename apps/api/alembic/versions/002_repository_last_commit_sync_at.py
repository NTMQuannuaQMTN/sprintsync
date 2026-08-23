"""Add repositories.last_commit_sync_at

Backs a cooldown on _sync_commits_from_github (commits.py) so that endpoint
stops hitting the real GitHub API (list + a per-new-commit detail fetch) on
every single page load of the Commits page — that was adding ~1s+ per visit
even with nothing new to sync, and much more with a backlog.

Revision ID: 002
Revises: 001
Create Date: 2026-08-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column("last_commit_sync_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("repositories", "last_commit_sync_at")
