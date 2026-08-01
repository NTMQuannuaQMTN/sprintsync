"""Initial schema — all core tables.

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable uuid-ossp extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Enums
    op.execute("CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done', 'blocked', 'cancelled')")
    op.execute("CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical')")
    op.execute("CREATE TYPE spec_status AS ENUM ('pending', 'processing', 'done', 'error')")
    op.execute("CREATE TYPE suggestion_status AS ENUM ('pending', 'approved', 'rejected')")
    op.execute("CREATE TYPE suggestion_action AS ENUM ('status_change', 'progress_update', 'add_comment')")
    op.execute("CREATE TYPE activity_type AS ENUM ('repo_connected', 'spec_uploaded', 'tasks_generated', 'commit_received', 'suggestion_created', 'suggestion_approved', 'suggestion_rejected', 'task_updated', 'webhook_installed')")
    op.execute("CREATE TYPE integration_type AS ENUM ('github', 'notion', 'jira', 'linear', 'clickup', 'confluence', 'gitlab')")

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("github_id", sa.Integer, nullable=False, unique=True),
        sa.Column("github_username", sa.String(255), nullable=False, unique=True),
        sa.Column("github_access_token", sa.Text, nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"])
    op.create_index("ix_users_github_username", "users", ["github_username"])
    op.create_index("ix_users_email", "users", ["email"])

    # repositories
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("github_repo_id", sa.Integer, nullable=False, unique=True),
        sa.Column("full_name", sa.String(512), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("default_branch", sa.String(255), nullable=False, server_default="main"),
        sa.Column("language", sa.String(100), nullable=True),
        sa.Column("stars", sa.Integer, nullable=False, server_default="0"),
        sa.Column("private", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("html_url", sa.Text, nullable=False),
        sa.Column("webhook_id", sa.Integer, nullable=True),
        sa.Column("webhook_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("health_score", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_repositories_owner_id", "repositories", ["owner_id"])
    op.create_index("ix_repositories_github_repo_id", "repositories", ["github_repo_id"])
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"])

    # project_specifications
    op.create_table(
        "project_specifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("storage_url", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("pending", "processing", "done", "error", name="spec_status"), nullable=False, server_default="pending"),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("task_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_project_specifications_repository_id", "project_specifications", ["repository_id"])

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spec_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_specifications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("todo", "in_progress", "done", "blocked", "cancelled", name="task_status"), nullable=False, server_default="todo"),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="task_priority"), nullable=False, server_default="medium"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ai_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("ai_context", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_repository_id", "tasks", ["repository_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_parent_id", "tasks", ["parent_id"])

    # commits
    op.create_table(
        "commits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sha", sa.String(40), nullable=False),
        sa.Column("short_sha", sa.String(8), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("author_name", sa.String(255), nullable=False),
        sa.Column("author_email", sa.String(255), nullable=False),
        sa.Column("author_avatar", sa.Text, nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("html_url", sa.Text, nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("additions", sa.Integer, server_default="0"),
        sa.Column("deletions", sa.Integer, server_default="0"),
        sa.Column("changed_files", sa.Integer, server_default="0"),
        sa.Column("files_changed", postgresql.JSONB, nullable=True),
        sa.Column("analyzed", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_commits_repository_sha", "commits", ["repository_id", "sha"], unique=True)

    # suggestions
    op.create_table(
        "suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("commit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", name="suggestion_status"), nullable=False, server_default="pending"),
        sa.Column("action", sa.Enum("status_change", "progress_update", "add_comment", name="suggestion_action"), nullable=False),
        sa.Column("proposed_status", sa.String(50), nullable=True),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_suggestions_repository_status", "suggestions", ["repository_id", "status"])
    op.create_index("ix_suggestions_task_id", "suggestions", ["task_id"])

    # activity_logs
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.Enum("repo_connected", "spec_uploaded", "tasks_generated", "commit_received", "suggestion_created", "suggestion_approved", "suggestion_rejected", "task_updated", "webhook_installed", name="activity_type"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_activity_logs_repository_id", "activity_logs", ["repository_id"])
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])

    # integrations
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("integration_type", sa.Enum("github", "notion", "jira", "linear", "clickup", "confluence", "gitlab", name="integration_type"), nullable=False),
        sa.Column("workspace_id", sa.String(255), nullable=True),
        sa.Column("workspace_name", sa.String(255), nullable=True),
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "integration_type", name="uq_integrations_user_type"),
    )
    op.create_index("ix_integrations_user_id", "integrations", ["user_id"])


def downgrade() -> None:
    op.drop_table("integrations")
    op.drop_table("activity_logs")
    op.drop_table("suggestions")
    op.drop_table("commits")
    op.drop_table("tasks")
    op.drop_table("project_specifications")
    op.drop_table("repositories")
    op.drop_table("users")

    # Drop enums
    for enum_name in ["integration_type", "activity_type", "suggestion_action", "suggestion_status", "spec_status", "task_priority", "task_status"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
