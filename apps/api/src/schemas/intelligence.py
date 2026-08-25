"""Project intelligence (Phase 10) response schemas — pure observed data,
no AI-inferred fields. See src/services/project_intelligence.py."""
from datetime import datetime
from typing import List

from pydantic import BaseModel


class StaleTaskOut(BaseModel):
    task_id: str
    title: str
    status: str
    last_updated_at: datetime
    days_since_update: int


class UnmatchedActivityOut(BaseModel):
    kind: str
    id: str
    identifier: str
    summary: str
    occurred_at: datetime


class LargeChangeOut(BaseModel):
    kind: str
    id: str
    identifier: str
    summary: str
    lines_changed: int
    occurred_at: datetime


class ProjectIntelligenceResponse(BaseModel):
    stale_tasks: List[StaleTaskOut]
    unmatched_activity: List[UnmatchedActivityOut]
    unusually_large_changes: List[LargeChangeOut]
