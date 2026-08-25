"""Pull request list/detail/summary endpoints.

V1/early-V2 had no read path for PullRequest at all — the webhook wrote
rows but nothing in the product could ever show them. This closes that
gap and gives Phase 9's summarize_pull_request a real caller.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.pull_request import PullRequest
from src.models.repository import Repository
from src.schemas.pull_request import PullRequestOut, SummaryOut
from src.services.ai_reasoning.summarization import summarize_pull_request
from src.services.ai_reasoning.prompt import build_diff_excerpt

router = APIRouter(prefix="/repositories/{repo_id}/pull_requests", tags=["pull_requests"])


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


async def _get_pr_or_404(repo_id: uuid.UUID, pr_id: uuid.UUID, db: AsyncSession) -> PullRequest:
    result = await db.execute(
        select(PullRequest).where(PullRequest.id == pr_id, PullRequest.repository_id == repo_id)
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr


@router.get("", response_model=List[PullRequestOut])
async def list_pull_requests(
    repo_id: uuid.UUID,
    limit: int = Query(30, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.repository_id == repo_id)
        .order_by(PullRequest.opened_at.desc())
        .limit(limit)
    )
    return [PullRequestOut.model_validate(pr) for pr in result.scalars().all()]


@router.get("/{pr_id}", response_model=PullRequestOut)
async def get_pull_request(
    repo_id: uuid.UUID,
    pr_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    pr = await _get_pr_or_404(repo_id, pr_id, db)
    return PullRequestOut.model_validate(pr)


@router.get("/{pr_id}/summary", response_model=SummaryOut)
async def get_pull_request_summary(
    repo_id: uuid.UUID,
    pr_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """AI (or heuristic-fallback) summary of what this PR does — computed
    on demand, not stored, so it always reflects current ANTHROPIC_API_KEY
    availability rather than a summary frozen at ingestion time."""
    await _assert_repo_owner(repo_id, user_id, db)
    pr = await _get_pr_or_404(repo_id, pr_id, db)
    diff_excerpt = build_diff_excerpt(pr.files_changed or [])
    result = await summarize_pull_request(
        title=pr.title, body=pr.body, files_changed=pr.files_changed or [], diff_excerpt=diff_excerpt
    )
    return SummaryOut(**result)
