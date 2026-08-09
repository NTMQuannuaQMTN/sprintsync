"""Suggestion Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from src.models.suggestion import SuggestionStatus, SuggestionAction


class SuggestionOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    task_id: Optional[uuid.UUID] = None
    commit_id: Optional[uuid.UUID] = None
    status: SuggestionStatus
    action: SuggestionAction
    proposed_status: Optional[str] = None
    explanation: str
    confidence_score: float
    evidence: Optional[dict] = None
    reviewed_at: Optional[datetime] = None
    reviewer_note: Optional[str] = None
    created_at: datetime

    # Populated via join
    task_title: Optional[str] = None
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None

    model_config = {"from_attributes": True}


class SuggestionReview(BaseModel):
    note: Optional[str] = None


class BulkReviewResult(BaseModel):
    count: int
