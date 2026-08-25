"""Add 'pr_received' to the activity_type enum

Postgres requires ALTER TYPE ... ADD VALUE to run outside a transaction
block (a value added inside the same transaction that also uses it would
fail — that's not our case here, since this migration never inserts a row,
but the ADD VALUE statement itself still must run non-transactionally on
most Postgres versions). Alembic's autocommit_block() handles that.

Downgrade is intentionally a no-op: Postgres has no ALTER TYPE ... DROP
VALUE. Removing an enum value safely requires rebuilding the type (rename,
recreate, migrate every dependent column, drop the old type) — standard,
accepted tradeoff for additive enum values; not worth the risk/complexity
for a downgrade path unlikely to ever be exercised.

Revision ID: 004
Revises: 003
Create Date: 2026-08-23 00:00:00.000000
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'pr_received'")


def downgrade() -> None:
    pass  # see module docstring — no safe DROP VALUE in Postgres
