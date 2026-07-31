"""Repository Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RepositoryBase(BaseModel):
    full_name: str
    name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    private: bool = False
    html_url: str
    default_branch: str = "main"


class RepositoryOut(RepositoryBase):
    id: uuid.UUID
    github_repo_id: int
    webhook_active: bool
    health_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # Computed fields (populated by service)
    task_count: Optional[int] = None
    done_count: Optional[int] = None
    pending_suggestions: Optional[int] = None
    recent_commit_sha: Optional[str] = None
    recent_commit_message: Optional[str] = None

    model_config = {"from_attributes": True}


class GitHubRepoItem(BaseModel):
    """GitHub API repo shape for listing available repos."""
    id: int
    full_name: str
    name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stargazers_count: int = 0
    private: bool = False
    html_url: str
    default_branch: str = "main"
    already_connected: bool = False
