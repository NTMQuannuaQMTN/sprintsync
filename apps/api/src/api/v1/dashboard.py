"""Dashboard aggregate data endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.repository import Repository
from src.models.task import Task, TaskStatus
from src.models.suggestion import Suggestion, SuggestionStatus
from src.models.commit import Commit
from src.models.activity_log import ActivityLog
from src.schemas.dashboard import DashboardResponse, DashboardStats, CommitSummary, ActivityItem
from src.schemas.repository import RepositoryOut
from src.schemas.suggestion import SuggestionOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate dashboard data for the current user."""

    # Repositories
    repos_result = await db.execute(
        select(Repository).where(Repository.owner_id == user_id).order_by(Repository.updated_at.desc()).limit(10)
    )
    repos = repos_result.scalars().all()
    repo_ids = [r.id for r in repos]

    # Task stats across all repos
    total_tasks = 0
    done_tasks = 0
    if repo_ids:
        total_q = await db.execute(
            select(func.count(Task.id)).where(Task.repository_id.in_(repo_ids))
        )
        total_tasks = total_q.scalar() or 0

        done_q = await db.execute(
            select(func.count(Task.id)).where(
                Task.repository_id.in_(repo_ids), Task.status == TaskStatus.DONE
            )
        )
        done_tasks = done_q.scalar() or 0

    # Pending suggestions
    pending_q = await db.execute(
        select(func.count(Suggestion.id)).where(
            Suggestion.repository_id.in_(repo_ids) if repo_ids else Suggestion.id.is_(None),
            Suggestion.status == SuggestionStatus.PENDING,
        )
    )
    pending_count = pending_q.scalar() or 0

    stats = DashboardStats(
        total_repos=len(repos),
        total_tasks=total_tasks,
        completed_tasks=done_tasks,
        pending_suggestions=pending_count,
        completion_rate=round(done_tasks / total_tasks * 100, 1) if total_tasks else 0.0,
    )

    # Enrich repo list
    repo_outs = []
    for repo in repos:
        tc = await db.execute(select(func.count(Task.id)).where(Task.repository_id == repo.id))
        dc = await db.execute(select(func.count(Task.id)).where(Task.repository_id == repo.id, Task.status == TaskStatus.DONE))
        pc = await db.execute(select(func.count(Suggestion.id)).where(Suggestion.repository_id == repo.id, Suggestion.status == SuggestionStatus.PENDING))

        ro = RepositoryOut.model_validate(repo)
        ro.task_count = tc.scalar() or 0
        ro.done_count = dc.scalar() or 0
        ro.pending_suggestions = pc.scalar() or 0
        repo_outs.append(ro)

    # Pending suggestions list
    sug_result = await db.execute(
        select(Suggestion)
        .where(
            Suggestion.repository_id.in_(repo_ids) if repo_ids else Suggestion.id.is_(None),
            Suggestion.status == SuggestionStatus.PENDING,
        )
        .order_by(Suggestion.confidence_score.desc())
        .limit(5)
    )
    pending_suggestions = [SuggestionOut.model_validate(s) for s in sug_result.scalars().all()]

    # Recent commits
    commit_result = await db.execute(
        select(Commit)
        .where(Commit.repository_id.in_(repo_ids) if repo_ids else Commit.id.is_(None))
        .order_by(Commit.committed_at.desc())
        .limit(10)
    )
    recent_commits = [CommitSummary.model_validate(c) for c in commit_result.scalars().all()]

    # Activity feed
    activity_result = await db.execute(
        select(ActivityLog, Repository.name)
        .outerjoin(Repository, ActivityLog.repository_id == Repository.id)
        .where(ActivityLog.repository_id.in_(repo_ids) if repo_ids else ActivityLog.id.is_(None))
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
    )
    recent_activity = []
    for row in activity_result.all():
        log, repo_name = row
        item = ActivityItem.model_validate(log)
        item.repository_name = repo_name
        recent_activity.append(item)

    return DashboardResponse(
        stats=stats,
        repositories=repo_outs,
        pending_suggestions=pending_suggestions,
        recent_commits=recent_commits,
        recent_activity=recent_activity,
    )
