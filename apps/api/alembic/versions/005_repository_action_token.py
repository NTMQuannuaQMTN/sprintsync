"""Add repositories.action_token

Backs V2 Phase 8's GitHub Action ingestion path: a per-repo bearer
credential the repo owner puts in their own GitHub Actions secrets, so
their own workflow can POST events to /webhook/action without SprintSync
needing GitHub App/OAuth webhook-install permission on the repo.

Revision ID: 005
Revises: 004
Create Date: 2026-08-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column("action_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_repositories_action_token", "repositories", ["action_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_repositories_action_token", table_name="repositories")
    op.drop_column("repositories", "action_token")
