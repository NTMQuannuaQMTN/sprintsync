"""Activity log endpoints."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.activity_log import ActivityLog, ActivityType
from src.models.repository import Repository
from src.schemas.dashboard import ActivityItem

router = APIRouter(prefix="/repositories/{repo_id}/activity", tags=["activity"])


@router.get("", response_model=List[ActivityItem])
async def list_activity(
    repo_id: uuid.UUID,
    limit: int = Query(50, le=100),
    event_type: Optional[ActivityType] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    repo_result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Repository not found")

    q = (
        select(ActivityLog)
        .where(ActivityLog.repository_id == repo_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    if event_type:
        q = q.where(ActivityLog.event_type == event_type)

    result = await db.execute(q)
    items = []
    for log in result.scalars().all():
        item = ActivityItem.model_validate(log)
        item.repository_name = repo.name
        items.append(item)
    return items
