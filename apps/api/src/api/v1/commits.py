"""Commit list/detail endpoints — exposes stored diff/changed-file data."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.models.commit import Commit
from src.models.task import Task, TaskStatus
from src.models.suggestion import Suggestion, SuggestionAction
from src.models.activity_log import ActivityLog, ActivityType
from src.schemas.commit import CommitOut, CommitAnalyzeResult
from src.services.ai import ai_service

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


@router.post("/analyze", response_model=CommitAnalyzeResult, status_code=status.HTTP_200_OK)
async def analyze_commits(
    repo_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """"Update to tasks" — run the same heuristic the webhook uses on every
    stored commit that hasn't been analyzed yet, against the repo's current
    open tasks, and file the results as pending suggestions for review (same
    approve/reject flow as suggestions.py — this never changes a task's
    status directly).
    """
    repo = await _assert_repo_owner(repo_id, user_id, db)

    commits_result = await db.execute(
        select(Commit)
        .where(Commit.repository_id == repo_id, Commit.analyzed.is_(False))
        .order_by(Commit.committed_at.asc())
        .limit(50)
    )
    commits = commits_result.scalars().all()
    if not commits:
        return CommitAnalyzeResult(commits_processed=0, suggestions_created=0)

    tasks_result = await db.execute(
        select(Task).where(
            Task.repository_id == repo_id,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
            Task.parent_id.is_(None),
        )
    )
    tasks_plain = [
        {"id": str(t.id), "title": t.title, "status": t.status.value}
        for t in tasks_result.scalars().all()
    ]

    suggestions_created = 0
    for commit in commits:
        suggested = await ai_service.analyze_commit(
            commit_message=commit.message,
            files_changed=commit.files_changed or [],
            tasks=tasks_plain,
        )
        for s in suggested:
            db.add(Suggestion(
                repository_id=repo_id,
                task_id=s["task_id"],
                commit_id=commit.id,
                action=SuggestionAction.STATUS_CHANGE,
                proposed_status=s["proposed_status"],
                explanation=s["explanation"],
                confidence_score=s["confidence"],
                evidence=s["evidence"],
            ))
            suggestions_created += 1
        commit.analyzed = True

    if suggestions_created > 0:
        db.add(ActivityLog(
            user_id=user_id,
            repository_id=repo_id,
            event_type=ActivityType.SUGGESTION_CREATED,
            title=f"AI created {suggestions_created} suggestion(s) for {repo.name}",
            description=f"From reviewing {len(commits)} commit(s)",
        ))

    await db.commit()
    return CommitAnalyzeResult(commits_processed=len(commits), suggestions_created=suggestions_created)


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
