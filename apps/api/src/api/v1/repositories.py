"""Repository CRUD and GitHub integration endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.core.config import settings
from src.models.user import User
from src.models.repository import Repository
from src.models.task import Task, TaskStatus
from src.models.suggestion import Suggestion, SuggestionStatus
from src.schemas.repository import RepositoryOut, GitHubRepoItem
from src.services.github import GitHubService
from src.models.activity_log import ActivityLog, ActivityType

router = APIRouter(prefix="/repositories", tags=["repositories"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=List[RepositoryOut])
async def list_repositories(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all connected repositories for current user."""
    result = await db.execute(
        select(Repository).where(Repository.owner_id == user_id).order_by(Repository.updated_at.desc())
    )
    repos = result.scalars().all()

    out = []
    for repo in repos:
        # Task counts
        task_result = await db.execute(
            select(func.count(Task.id)).where(Task.repository_id == repo.id)
        )
        total_tasks = task_result.scalar() or 0

        done_result = await db.execute(
            select(func.count(Task.id)).where(
                Task.repository_id == repo.id, Task.status == TaskStatus.DONE
            )
        )
        done_tasks = done_result.scalar() or 0

        pending_result = await db.execute(
            select(func.count(Suggestion.id)).where(
                Suggestion.repository_id == repo.id,
                Suggestion.status == SuggestionStatus.PENDING,
            )
        )
        pending_suggestions = pending_result.scalar() or 0

        repo_out = RepositoryOut.model_validate(repo)
        repo_out.task_count = total_tasks
        repo_out.done_count = done_tasks
        repo_out.pending_suggestions = pending_suggestions
        out.append(repo_out)

    return out


@router.get("/github/available", response_model=List[GitHubRepoItem])
async def list_github_repos(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List user's GitHub repos with connected status."""
    user = await _get_user(user_id, db)
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="No GitHub access token")

    gh = GitHubService(user.github_access_token)
    try:
        gh_repos = await gh.list_repos()
    finally:
        await gh.close()

    # Get already-connected repo IDs
    connected_result = await db.execute(
        select(Repository.github_repo_id).where(Repository.owner_id == user_id)
    )
    connected_ids = {r for r in connected_result.scalars().all()}

    return [
        GitHubRepoItem(
            id=r["id"],
            full_name=r["full_name"],
            name=r["name"],
            description=r.get("description"),
            language=r.get("language"),
            stargazers_count=r.get("stargazers_count", 0),
            private=r.get("private", False),
            html_url=r["html_url"],
            default_branch=r.get("default_branch", "main"),
            already_connected=r["id"] in connected_ids,
        )
        for r in gh_repos
    ]


@router.post("", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def connect_repository(
    github_repo_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Connect a GitHub repository to SprintSync."""
    user = await _get_user(user_id, db)

    # Check if already connected
    existing = await db.execute(
        select(Repository).where(Repository.github_repo_id == github_repo_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Repository already connected")

    gh = GitHubService(user.github_access_token)
    try:
        # Get full repo details from GitHub
        gh_repos = await gh.list_repos()
        gh_repo = next((r for r in gh_repos if r["id"] == github_repo_id), None)
        if not gh_repo:
            raise HTTPException(status_code=404, detail="Repository not found on GitHub")

        repo = Repository(
            owner_id=user_id,
            github_repo_id=gh_repo["id"],
            full_name=gh_repo["full_name"],
            name=gh_repo["name"],
            description=gh_repo.get("description"),
            default_branch=gh_repo.get("default_branch", "main"),
            language=gh_repo.get("language"),
            stars=gh_repo.get("stargazers_count", 0),
            private=gh_repo.get("private", False),
            html_url=gh_repo["html_url"],
        )

        # Install webhook if secret configured
        if settings.GITHUB_WEBHOOK_SECRET:
            webhook_url = f"{settings.FRONTEND_URL}/api/v1/webhook/github"
            try:
                hook = await gh.install_webhook(gh_repo["full_name"], webhook_url)
                repo.webhook_id = hook["id"]
                repo.webhook_active = True
            except Exception:
                pass  # webhook install is non-blocking

        db.add(repo)

        # Log activity
        log = ActivityLog(
            user_id=user_id,
            event_type=ActivityType.REPO_CONNECTED,
            title=f"Connected repository {gh_repo['full_name']}",
            description=f"Repository {gh_repo['full_name']} has been connected to SprintSync.",
        )
        db.add(log)

        await db.commit()
        await db.refresh(repo)

    finally:
        await gh.close()

    return RepositoryOut.model_validate(repo)


@router.get("/{repo_id}", response_model=RepositoryOut)
async def get_repository(
    repo_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Enrich with counts
    task_result = await db.execute(
        select(func.count(Task.id)).where(Task.repository_id == repo_id)
    )
    done_result = await db.execute(
        select(func.count(Task.id)).where(Task.repository_id == repo_id, Task.status == TaskStatus.DONE)
    )
    pending_result = await db.execute(
        select(func.count(Suggestion.id)).where(
            Suggestion.repository_id == repo_id, Suggestion.status == SuggestionStatus.PENDING
        )
    )

    repo_out = RepositoryOut.model_validate(repo)
    repo_out.task_count = task_result.scalar() or 0
    repo_out.done_count = done_result.scalar() or 0
    repo_out.pending_suggestions = pending_result.scalar() or 0
    return repo_out


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_repository(
    repo_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Remove webhook
    if repo.webhook_id and repo.webhook_active:
        user = await _get_user(user_id, db)
        gh = GitHubService(user.github_access_token)
        try:
            await gh.delete_webhook(repo.full_name, repo.webhook_id)
        except Exception:
            pass
        finally:
            await gh.close()

    await db.delete(repo)
    await db.commit()
