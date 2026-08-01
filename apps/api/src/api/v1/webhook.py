"""GitHub Webhook handler — processes push events and triggers AI analysis."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.models.repository import Repository
from src.models.commit import Commit
from src.models.task import Task, TaskStatus
from src.models.suggestion import Suggestion, SuggestionAction
from src.models.activity_log import ActivityLog, ActivityType
from src.models.user import User
from src.services.github import verify_webhook_signature, GitHubService
from src.services.ai import ai_service

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive GitHub webhook push events and create AI suggestions."""
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "push":
        return {"status": "ignored", "event": event_type}

    payload = await request.json()
    repo_full_name = payload.get("repository", {}).get("full_name")
    branch = payload.get("ref", "").replace("refs/heads/", "")

    if not repo_full_name:
        return {"status": "skipped", "reason": "no repo name"}

    # Find the connected repository
    result = await db.execute(
        select(Repository).where(Repository.full_name == repo_full_name)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        return {"status": "skipped", "reason": "repo not connected"}

    commits_data = payload.get("commits", [])
    new_suggestions = 0

    # GitHub push webhook payloads only carry filenames (added/modified/removed),
    # never line-level diff content. To make the real diff/patch retrievable we
    # fetch it via the REST API using the repo owner's stored OAuth token —
    # best-effort: on any failure we fall back to the filename-only data above,
    # exactly like the webhook-install and Supabase-upload code paths elsewhere
    # in this codebase.
    gh: Optional[GitHubService] = None
    owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    if owner and owner.github_access_token:
        gh = GitHubService(owner.github_access_token)

    try:
        for commit_data in commits_data:
            sha = commit_data.get("id", "")
            if not sha:
                continue

            # Dedup
            existing = await db.execute(
                select(Commit).where(Commit.repository_id == repo.id, Commit.sha == sha)
            )
            if existing.scalar_one_or_none():
                continue

            # Parse committed_at
            committed_raw = commit_data.get("timestamp", "")
            try:
                committed_at = datetime.fromisoformat(committed_raw.replace("Z", "+00:00"))
            except Exception:
                committed_at = datetime.now(timezone.utc)

            # Files changed from payload (fallback — filenames only, no diff)
            added = commit_data.get("added", [])
            modified = commit_data.get("modified", [])
            removed = commit_data.get("removed", [])
            all_files = [{"filename": f, "status": "added"} for f in added]
            all_files += [{"filename": f, "status": "modified"} for f in modified]
            all_files += [{"filename": f, "status": "removed"} for f in removed]
            additions = 0
            deletions = 0

            # Try to enrich with the real diff/patch + line stats from the GitHub API.
            if gh:
                try:
                    detail = await gh.get_commit_detail(repo_full_name, sha)
                    stats = detail.get("stats", {})
                    additions = stats.get("additions", 0)
                    deletions = stats.get("deletions", 0)
                    all_files = [
                        {
                            "filename": f.get("filename", ""),
                            "status": f.get("status", ""),
                            "additions": f.get("additions", 0),
                            "deletions": f.get("deletions", 0),
                            "patch": f.get("patch"),
                        }
                        for f in detail.get("files", [])
                    ]
                except Exception:
                    pass  # diff enrichment is best-effort; filename-only fallback stands

            commit = Commit(
                repository_id=repo.id,
                sha=sha,
                short_sha=sha[:7],
                message=commit_data.get("message", ""),
                author_name=commit_data.get("author", {}).get("name", ""),
                author_email=commit_data.get("author", {}).get("email", ""),
                committed_at=committed_at,
                html_url=commit_data.get("url", ""),
                branch=branch,
                changed_files=len(all_files),
                additions=additions,
                deletions=deletions,
                files_changed=all_files,
            )
            db.add(commit)

            # Get open tasks for this repo
            tasks_result = await db.execute(
                select(Task).where(
                    Task.repository_id == repo.id,
                    Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
                    Task.parent_id.is_(None),
                )
            )
            open_tasks = tasks_result.scalars().all()
            tasks_plain = [{"id": str(t.id), "title": t.title, "status": t.status.value} for t in open_tasks]

            # AI analysis
            suggested = await ai_service.analyze_commit(
                commit_message=commit_data.get("message", ""),
                files_changed=all_files,
                tasks=tasks_plain,
            )

            for s in suggested:
                suggestion = Suggestion(
                    repository_id=repo.id,
                    task_id=s["task_id"],
                    action=SuggestionAction.STATUS_CHANGE,
                    proposed_status=s["proposed_status"],
                    explanation=s["explanation"],
                    confidence_score=s["confidence"],
                    evidence=s["evidence"],
                )
                db.add(suggestion)
                new_suggestions += 1

            # Activity log
            db.add(ActivityLog(
                repository_id=repo.id,
                event_type=ActivityType.COMMIT_RECEIVED,
                title=f"New commit: {sha[:7]} — {commit_data.get('message', '')[:60]}",
                description=f"{len(all_files)} files changed",
            ))

            if new_suggestions > 0:
                db.add(ActivityLog(
                    repository_id=repo.id,
                    event_type=ActivityType.SUGGESTION_CREATED,
                    title=f"AI created {new_suggestions} suggestion(s)",
                    description=f"Based on commit {sha[:7]}",
                ))
    finally:
        if gh:
            await gh.close()

    await db.commit()
    return {"status": "ok", "commits_processed": len(commits_data), "suggestions_created": new_suggestions}
