"""Repository-level daily/weekly activity digest (V2 Phase 9)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.commit import Commit
from src.models.pull_request import PullRequest, PullRequestState
from src.models.repository import Repository
from src.models.task import Task, TaskStatus
from src.schemas.pull_request import SummaryOut
from src.services.ai_reasoning.summarization import summarize_digest

router = APIRouter(prefix="/repositories/{repo_id}/summary", tags=["summary"])

_PERIOD_DAYS = {"day": 1, "week": 7}


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=SummaryOut)
async def get_repository_digest(
    repo_id: uuid.UUID,
    period: Literal["day", "week"] = Query("day"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = await _assert_repo_owner(repo_id, user_id, db)
    cutoff = datetime.now(timezone.utc) - timedelta(days=_PERIOD_DAYS[period])

    commit_count = (
        await db.execute(
            select(func.count(Commit.id)).where(Commit.repository_id == repo_id, Commit.committed_at >= cutoff)
        )
    ).scalar() or 0

    pr_opened_count = (
        await db.execute(
            select(func.count(PullRequest.id)).where(
                PullRequest.repository_id == repo_id, PullRequest.opened_at >= cutoff
            )
        )
    ).scalar() or 0

    pr_merged_count = (
        await db.execute(
            select(func.count(PullRequest.id)).where(
                PullRequest.repository_id == repo_id,
                PullRequest.state == PullRequestState.MERGED,
                PullRequest.closed_at >= cutoff,
            )
        )
    ).scalar() or 0

    tasks_done_count = (
        await db.execute(
            select(func.count(Task.id)).where(
                Task.repository_id == repo_id, Task.status == TaskStatus.DONE, Task.updated_at >= cutoff
            )
        )
    ).scalar() or 0

    tasks_in_progress_count = (
        await db.execute(
            select(func.count(Task.id)).where(
                Task.repository_id == repo_id, Task.status == TaskStatus.IN_PROGRESS
            )
        )
    ).scalar() or 0

    result = summarize_digest(
        repo_name=repo.name,
        period_label="today" if period == "day" else "this week",
        commit_count=commit_count,
        pr_opened_count=pr_opened_count,
        pr_merged_count=pr_merged_count,
        tasks_done_count=tasks_done_count,
        tasks_in_progress_count=tasks_in_progress_count,
    )
    return SummaryOut(**result)
