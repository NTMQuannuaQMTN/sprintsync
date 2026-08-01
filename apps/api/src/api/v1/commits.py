"""Commit list/detail endpoints — exposes stored diff/changed-file data."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.models.commit import Commit
from src.schemas.commit import CommitOut

router = APIRouter(prefix="/repositories/{repo_id}/commits", tags=["commits"])


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=List[CommitOut])
async def list_commits(
    repo_id: uuid.UUID,
    limit: int = Query(30, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Commit)
        .where(Commit.repository_id == repo_id)
        .order_by(Commit.committed_at.desc())
        .limit(limit)
    )
    return [CommitOut.model_validate(c) for c in result.scalars().all()]


@router.get("/{commit_id}", response_model=CommitOut)
async def get_commit(
    repo_id: uuid.UUID,
    commit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single commit, including its changed-files list and (when the
    webhook was able to reach the GitHub API) per-file patch/diff content."""
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Commit).where(Commit.id == commit_id, Commit.repository_id == repo_id)
    )
    commit = result.scalar_one_or_none()
    if not commit:
        raise HTTPException(status_code=404, detail="Commit not found")
    return CommitOut.model_validate(commit)
