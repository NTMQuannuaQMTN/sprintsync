"""Import all models to ensure Alembic detects them."""
from src.models.base import UUIDMixin, TimestampMixin
from src.models.user import User
from src.models.repository import Repository
from src.models.project_spec import ProjectSpecification, SpecStatus
from src.models.task import Task, TaskStatus, TaskPriority
from src.models.commit import Commit
from src.models.suggestion import Suggestion, SuggestionStatus, SuggestionAction
from src.models.activity_log import ActivityLog, ActivityType
from src.models.integration import Integration, IntegrationType

__all__ = [
    "UUIDMixin",
    "TimestampMixin",
    "User",
    "Repository",
    "ProjectSpecification",
    "SpecStatus",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Commit",
    "Suggestion",
    "SuggestionStatus",
    "SuggestionAction",
    "ActivityLog",
    "ActivityType",
    "Integration",
    "IntegrationType",
]
