"""Suggestion CRUD and review endpoints."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.models.suggestion import Suggestion, SuggestionStatus
from src.models.task import Task
from src.models.commit import Commit
from src.models.activity_log import ActivityLog, ActivityType
from src.schemas.suggestion import SuggestionOut, SuggestionReview, BulkReviewResult

router = APIRouter(prefix="/repositories/{repo_id}/suggestions", tags=["suggestions"])


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


async def _enrich(suggestion: Suggestion, db: AsyncSession) -> SuggestionOut:
    out = SuggestionOut.model_validate(suggestion)
    if suggestion.task_id:
        tr = await db.execute(select(Task.title).where(Task.id == suggestion.task_id))
        out.task_title = tr.scalar_one_or_none()
    if suggestion.commit_id:
        cr = await db.execute(
            select(Commit.sha, Commit.message).where(Commit.id == suggestion.commit_id)
        )
        row = cr.first()
        if row:
            out.commit_sha = row[0][:7]
            out.commit_message = row[1]
    return out


@router.get("", response_model=List[SuggestionOut])
async def list_suggestions(
    repo_id: uuid.UUID,
    status: Optional[SuggestionStatus] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)

    q = (
        select(Suggestion)
        .where(Suggestion.repository_id == repo_id)
        .order_by(Suggestion.created_at.desc())
    )
    if status:
        q = q.where(Suggestion.status == status)

    result = await db.execute(q)
    suggestions = result.scalars().all()
    return [await _enrich(s, db) for s in suggestions]


@router.post("/approve-all", response_model=BulkReviewResult)
async def approve_all_suggestions(
    repo_id: uuid.UUID,
    body: SuggestionReview = SuggestionReview(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Approve every currently pending suggestion for this repo — same
    per-suggestion effect as POST /{suggestion_id}/approve (applies the
    proposed task status change), just batched with one activity log entry
    instead of one per suggestion."""
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Suggestion).where(
            Suggestion.repository_id == repo_id, Suggestion.status == SuggestionStatus.PENDING
        )
    )
    pending = result.scalars().all()
    if not pending:
        return BulkReviewResult(count=0)

    now = datetime.now(timezone.utc)
    for suggestion in pending:
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.reviewed_at = now
        suggestion.reviewed_by = user_id
        suggestion.reviewer_note = body.note
        if suggestion.task_id and suggestion.proposed_status:
            tr = await db.execute(select(Task).where(Task.id == suggestion.task_id))
            task = tr.scalar_one_or_none()
            if task:
                task.status = suggestion.proposed_status  # type: ignore

    db.add(ActivityLog(
        user_id=user_id,
        repository_id=repo_id,
        event_type=ActivityType.SUGGESTION_APPROVED,
        title=f"{len(pending)} suggestion(s) approved in bulk",
    ))

    await db.commit()
    return BulkReviewResult(count=len(pending))


@router.post("/reject-all", response_model=BulkReviewResult)
async def reject_all_suggestions(
    repo_id: uuid.UUID,
    body: SuggestionReview = SuggestionReview(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reject every currently pending suggestion for this repo. Never
    touches any task — same as the single-suggestion reject endpoint."""
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Suggestion).where(
            Suggestion.repository_id == repo_id, Suggestion.status == SuggestionStatus.PENDING
        )
    )
    pending = result.scalars().all()
    if not pending:
        return BulkReviewResult(count=0)

    now = datetime.now(timezone.utc)
    for suggestion in pending:
        suggestion.status = SuggestionStatus.REJECTED
        suggestion.reviewed_at = now
        suggestion.reviewed_by = user_id
        suggestion.reviewer_note = body.note

    db.add(ActivityLog(
        user_id=user_id,
        repository_id=repo_id,
        event_type=ActivityType.SUGGESTION_REJECTED,
        title=f"{len(pending)} suggestion(s) rejected in bulk",
        description=body.note,
    ))

    await db.commit()
    return BulkReviewResult(count=len(pending))


@router.get("/{suggestion_id}", response_model=SuggestionOut)
async def get_suggestion(
    repo_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Suggestion).where(
            Suggestion.id == suggestion_id, Suggestion.repository_id == repo_id
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return await _enrich(s, db)


@router.post("/{suggestion_id}/approve", response_model=SuggestionOut)
async def approve_suggestion(
    repo_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    body: SuggestionReview = SuggestionReview(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Approve a suggestion — apply the proposed task status change."""
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Suggestion).where(
            Suggestion.id == suggestion_id, Suggestion.repository_id == repo_id
        )
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Suggestion already reviewed")

    suggestion.status = SuggestionStatus.APPROVED
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.reviewed_by = user_id
    suggestion.reviewer_note = body.note

    # Apply the proposed task status change
    if suggestion.task_id and suggestion.proposed_status:
        tr = await db.execute(select(Task).where(Task.id == suggestion.task_id))
        task = tr.scalar_one_or_none()
        if task:
            task.status = suggestion.proposed_status  # type: ignore

    # Activity log
    db.add(ActivityLog(
        user_id=user_id,
        repository_id=repo_id,
        event_type=ActivityType.SUGGESTION_APPROVED,
        title="Suggestion approved",
        description=suggestion.explanation[:200],
    ))

    await db.commit()
    await db.refresh(suggestion)
    return await _enrich(suggestion, db)


@router.post("/{suggestion_id}/reject", response_model=SuggestionOut)
async def reject_suggestion(
    repo_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    body: SuggestionReview = SuggestionReview(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Suggestion).where(
            Suggestion.id == suggestion_id, Suggestion.repository_id == repo_id
        )
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Suggestion already reviewed")

    suggestion.status = SuggestionStatus.REJECTED
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.reviewed_by = user_id
    suggestion.reviewer_note = body.note

    db.add(ActivityLog(
        user_id=user_id,
        repository_id=repo_id,
        event_type=ActivityType.SUGGESTION_REJECTED,
        title="Suggestion rejected",
        description=body.note or suggestion.explanation[:100],
    ))

    await db.commit()
    await db.refresh(suggestion)
    return await _enrich(suggestion, db)
