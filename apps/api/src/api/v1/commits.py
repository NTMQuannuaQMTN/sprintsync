"""Commit list/detail endpoints — exposes stored diff/changed-file data."""
import asyncio
import uuid
from datetime import datetime, timezone
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
from src.models.profile import Profile
from src.schemas.commit import CommitOut, CommitAnalyzeResult
from src.schemas.pull_request import SummaryOut
from src.services.ai_reasoning.reasoning import analyze_activity
from src.services.ai_reasoning.prompt import build_diff_excerpt
from src.services.ai_reasoning.summarization import summarize_commit
from src.services.github import GitHubService

router = APIRouter(prefix="/repositories/{repo_id}/commits", tags=["commits"])

# How long _sync_commits_from_github lets a repo go between real GitHub
# round-trips. Without this, every single page load of the Commits page
# paid for a live GitHub API call (list-commits, plus a per-new-commit
# detail fetch) even when nothing had changed — ~1s+ per visit measured
# locally, worse with a backlog of unsynced commits.
COMMIT_SYNC_COOLDOWN_SECONDS = 60


async def _assert_repo_owner(repo_id: uuid.UUID, user_id: str, db: AsyncSession) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


async def _sync_commits_from_github(repo: Repository, db: AsyncSession) -> None:
    """Best-effort backfill: without this, a commit only ever appears in our
    DB if a push-event webhook happened to fire for it (webhook.py) — a
    repo's existing history at connect time, or any repo whose webhook isn't
    actively delivering, would otherwise show nothing. Pulls the latest
    commits straight from GitHub's list-commits API (GitHubService.get_commits,
    previously written but never actually called anywhere) and inserts
    whichever ones aren't already stored, enriched with the same per-file
    diff/stat data webhook.py fetches for a live push.
    """
    now = datetime.now(timezone.utc)
    if repo.last_commit_sync_at is not None:
        elapsed = (now - repo.last_commit_sync_at).total_seconds()
        if elapsed < COMMIT_SYNC_COOLDOWN_SECONDS:
            return  # synced recently enough — skip the GitHub round-trip entirely

    owner_result = await db.execute(select(Profile).where(Profile.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    if not owner or not owner.github_access_token:
        return

    gh = GitHubService(owner.github_access_token)
    try:
        try:
            remote_commits = await gh.get_commits(repo.full_name, branch=repo.default_branch, per_page=30)
        except Exception:
            return  # GitHub unreachable, token revoked, branch renamed, etc. — non-fatal
        finally:
            # Set regardless of outcome (including the except above) so a
            # broken/rate-limited call also gets a cooldown instead of
            # retrying on every single request.
            repo.last_commit_sync_at = now
            await db.commit()

        shas = [rc.get("sha", "") for rc in remote_commits if rc.get("sha")]
        if not shas:
            return
        existing_result = await db.execute(
            select(Commit.sha).where(Commit.repository_id == repo.id, Commit.sha.in_(shas))
        )
        existing_shas = {row[0] for row in existing_result.all()}
        new_commits = [rc for rc in remote_commits if rc.get("sha") not in existing_shas]
        if not new_commits:
            return

        details = await asyncio.gather(
            *(gh.get_commit_detail(repo.full_name, rc["sha"]) for rc in new_commits),
            return_exceptions=True,
        )

        for rc, detail in zip(new_commits, details):
            sha = rc["sha"]
            commit_info = rc.get("commit", {})
            author_info = commit_info.get("author", {})
            try:
                committed_at = datetime.fromisoformat(author_info.get("date", "").replace("Z", "+00:00"))
            except Exception:
                committed_at = datetime.now(timezone.utc)

            additions = deletions = 0
            files: list = []
            # isinstance(detail, dict) — a positive check, not "not an
            # Exception" — is what actually lets mypy narrow `detail` here;
            # asyncio.gather(..., return_exceptions=True) types each result
            # as dict | BaseException, and "not Exception" doesn't rule out
            # every BaseException subtype.
            if isinstance(detail, dict):
                stats = detail.get("stats", {})
                additions = stats.get("additions", 0)
                deletions = stats.get("deletions", 0)
                files = [
                    {
                        "filename": f.get("filename", ""),
                        "status": f.get("status", ""),
                        "additions": f.get("additions", 0),
                        "deletions": f.get("deletions", 0),
                        "patch": f.get("patch"),
                    }
                    for f in detail.get("files", [])
                ]

            db.add(Commit(
                repository_id=repo.id,
                sha=sha,
                short_sha=sha[:7],
                message=commit_info.get("message", ""),
                author_name=author_info.get("name", ""),
                author_email=author_info.get("email", ""),
                author_avatar=(rc.get("author") or {}).get("avatar_url"),
                committed_at=committed_at,
                html_url=rc.get("html_url", ""),
                branch=repo.default_branch,
                changed_files=len(files),
                additions=additions,
                deletions=deletions,
                files_changed=files,
            ))
        await db.commit()
    finally:
        await gh.close()


@router.get("", response_model=List[CommitOut])
async def list_commits(
    repo_id: uuid.UUID,
    limit: int = Query(30, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = await _assert_repo_owner(repo_id, user_id, db)
    await _sync_commits_from_github(repo, db)
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
        files_changed = commit.files_changed or []
        suggested = await analyze_activity(
            activity_type="commit",
            text_signals=[commit.message],
            tasks=tasks_plain,
            event_key="push",
            changed_files=[f.get("filename", "") for f in files_changed],
            files_with_patches=files_changed,
            repo_status_mapping=repo.status_mapping,
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


@router.get("/{commit_id}/summary", response_model=SummaryOut)
async def get_commit_summary(
    repo_id: uuid.UUID,
    commit_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """AI (or heuristic-fallback) summary of what this commit does —
    computed on demand, same pattern as the PR summary endpoint."""
    await _assert_repo_owner(repo_id, user_id, db)
    result = await db.execute(
        select(Commit).where(Commit.id == commit_id, Commit.repository_id == repo_id)
    )
    commit = result.scalar_one_or_none()
    if not commit:
        raise HTTPException(status_code=404, detail="Commit not found")
    diff_excerpt = build_diff_excerpt(commit.files_changed or [])
    summary_result = await summarize_commit(
        message=commit.message, files_changed=commit.files_changed or [], diff_excerpt=diff_excerpt
    )
    return SummaryOut(**summary_result)
