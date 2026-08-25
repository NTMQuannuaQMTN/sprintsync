"""Project intelligence endpoint (V2 Phase 10) — surfaces pure DB-derived
observations (stale tasks, unmatched activity, unusually large changes) for
a repository. See src/services/project_intelligence.py for the "these are
facts, not AI inference" boundary this deliberately maintains.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.schemas.intelligence import (
    LargeChangeOut,
    ProjectIntelligenceResponse,
    StaleTaskOut,
    UnmatchedActivityOut,
)
from src.services import project_intelligence

router = APIRouter(prefix="/repositories/{repo_id}/intelligence", tags=["intelligence"])


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=ProjectIntelligenceResponse)
async def get_project_intelligence(
    repo_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)

    stale = await project_intelligence.get_stale_tasks(db, repo_id)
    unmatched = await project_intelligence.get_unmatched_activity(db, repo_id)
    large = await project_intelligence.get_unusually_large_changes(db, repo_id)

    return ProjectIntelligenceResponse(
        stale_tasks=[StaleTaskOut(**t.__dict__) for t in stale],
        unmatched_activity=[UnmatchedActivityOut(**a.__dict__) for a in unmatched],
        unusually_large_changes=[LargeChangeOut(**c.__dict__) for c in large],
    )
