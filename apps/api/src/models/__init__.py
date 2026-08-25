"""Import all models to ensure Alembic detects them."""
from src.models.base import UUIDMixin, TimestampMixin
from src.models.profile import Profile
from src.models.repository import Repository
from src.models.project_spec import ProjectSpecification, SpecStatus
from src.models.task import Task, TaskStatus, TaskPriority
from src.models.commit import Commit
from src.models.pull_request import PullRequest, PullRequestState
from src.models.suggestion import Suggestion, SuggestionStatus, SuggestionAction
from src.models.activity_log import ActivityLog, ActivityType
from src.models.integration import Integration, IntegrationType
from src.models.webhook_delivery import WebhookDelivery

__all__ = [
    "UUIDMixin",
    "TimestampMixin",
    "Profile",
    "Repository",
    "ProjectSpecification",
    "SpecStatus",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Commit",
    "PullRequest",
    "PullRequestState",
    "Suggestion",
    "SuggestionStatus",
    "SuggestionAction",
    "ActivityLog",
    "ActivityType",
    "Integration",
    "IntegrationType",
    "WebhookDelivery",
]
