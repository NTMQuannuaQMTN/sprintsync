"""ProjectSpecification Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from src.models.project_spec import SpecStatus
from src.schemas.task import TaskCreate


class SpecOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    filename: str
    file_size: Optional[int] = None
    mime_type: str
    storage_url: Optional[str] = None
    status: SpecStatus
    ai_summary: Optional[str] = None
    task_count: int
    error_message: Optional[str] = None
    created_at: datetime

    # AI-extracted tasks awaiting human review — NOT yet persisted as Task rows.
    # Populated only by the upload endpoint's response; empty on list/get.
    draft_tasks: List[TaskCreate] = []

    model_config = {"from_attributes": True}
