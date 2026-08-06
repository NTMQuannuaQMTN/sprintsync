"""Commit Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CommitFile(BaseModel):
    filename: str
    status: str
    additions: int = 0
    deletions: int = 0
    patch: Optional[str] = None


class CommitAnalyzeResult(BaseModel):
    commits_processed: int
    suggestions_created: int


class CommitOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    sha: str
    short_sha: str
    message: str
    author_name: str
    author_email: str
    author_avatar: Optional[str] = None
    committed_at: datetime
    html_url: str
    branch: str
    additions: int
    deletions: int
    changed_files: int
    files_changed: Optional[List[CommitFile]] = None
    analyzed: bool

    model_config = {"from_attributes": True}
