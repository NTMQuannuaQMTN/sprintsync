"""ProjectSpecification Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from src.models.project_spec import SpecStatus


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

    model_config = {"from_attributes": True}
