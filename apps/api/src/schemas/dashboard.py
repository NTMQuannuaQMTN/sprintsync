"""Dashboard aggregate schemas."""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from src.schemas.repository import RepositoryOut
from src.schemas.suggestion import SuggestionOut


class CommitSummary(BaseModel):
    id: uuid.UUID
    sha: str
    short_sha: str
    message: str
    author_name: str
    author_avatar: Optional[str] = None
    committed_at: datetime
    additions: int
    deletions: int
    html_url: str

    model_config = {"from_attributes": True}


class ActivityItem(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    description: Optional[str] = None
    created_at: datetime
    repository_name: Optional[str] = None

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_repos: int
    total_tasks: int
    completed_tasks: int
    pending_suggestions: int
    completion_rate: float  # 0-100


class DashboardResponse(BaseModel):
    stats: DashboardStats
    repositories: List[RepositoryOut]
    pending_suggestions: List[SuggestionOut]
    recent_commits: List[CommitSummary]
    recent_activity: List[ActivityItem]
