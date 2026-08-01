"""Task Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from src.models.task import TaskStatus, TaskPriority


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[uuid.UUID] = None
    order_index: int = 0
    ai_tags: Optional[List[str]] = None
    ai_context: Optional[dict] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    order_index: Optional[int] = None


class TaskOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    spec_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    order_index: int
    ai_tags: Optional[List[str]] = None
    subtasks: List["TaskOut"] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


TaskOut.model_rebuild()


class TaskBulkCreate(BaseModel):
    tasks: List[TaskCreate]
    spec_id: Optional[uuid.UUID] = None
