"""PullRequest Pydantic schemas."""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from src.models.pull_request import PullRequestState
from src.schemas.commit import CommitFile


class PullRequestOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    number: int
    title: str
    body: Optional[str] = None
    author: str
    html_url: str
    branch: str
    base_branch: str
    state: PullRequestState
    merged: bool
    additions: int
    deletions: int
    changed_files: int
    files_changed: Optional[List[CommitFile]] = None
    opened_at: datetime
    updated_at_github: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    analyzed: bool

    model_config = {"from_attributes": True}


class SummaryOut(BaseModel):
    summary: str
    source: str  # "llm" | "heuristic"
