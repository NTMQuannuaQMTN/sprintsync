"""GitHub Webhook handler — processes push and pull_request events.

V2 changes from V1:
- Generic delivery-level idempotency (WebhookDelivery, keyed on GitHub's
  X-GitHub-Delivery header) checked before any event-specific processing —
  previously the only dedup was Commit.sha uniqueness, which does nothing
  for PR events and doesn't protect a retried delivery from re-running
  partial work before its commits were persisted.
- pull_request events (opened/synchronize/closed/reopened) are now
  ingested, not just push.
- Analysis goes through services/ai_reasoning (real structured LLM
  reasoning when ANTHROPIC_API_KEY is configured, heuristic fallback
  otherwise) instead of the old ai.py's message-and-filename-only heuristic.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from src.core.database import get_db
from src.models.repository import Repository
from src.models.commit import Commit
from src.models.pull_request import PullRequest, PullRequestState
from src.models.task import Task, TaskStatus
from src.models.suggestion import Suggestion, SuggestionAction
from src.models.activity_log import ActivityLog, ActivityType
from src.models.profile import Profile
from src.models.webhook_delivery import WebhookDelivery
from src.services.github import verify_webhook_signature, GitHubService
from src.services.ai_reasoning.reasoning import analyze_activity

router = APIRouter(prefix="/webhook", tags=["webhook"])

_HANDLED_PR_ACTIONS = {"opened", "synchronize", "closed", "reopened"}
_EVENT_KEY_BY_PR_ACTION = {
    "opened": "pr_opened",
    "reopened": "pr_opened",
    "synchronize": "pr_synchronize",
    # "closed" is resolved to pr_merged/pr_closed based on the merged flag — see _handle_pull_request
}


async def _is_duplicate_delivery(
    db: AsyncSession, delivery_id: str, event_type: str, repository_id
) -> bool:
    """Records this delivery and returns True if it was already recorded —
    an INSERT that violates the unique constraint means a prior request
    (or a concurrent race) already claimed this exact delivery. Without a
    delivery id (some senders omit it, though GitHub always includes one)
    dedup is impossible, so it proceeds rather than blocking everything."""
    if not delivery_id:
        return False
    db.add(WebhookDelivery(delivery_id=delivery_id, event_type=event_type, repository_id=repository_id))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return True
    return False


@router.post("/github")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive GitHub webhook push/pull_request events and create AI
    suggestions."""
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload")

    repo_full_name = (payload.get("repository") or {}).get("full_name")
    if not repo_full_name:
        return {"status": "skipped", "reason": "no repo name"}

    result = await db.execute(select(Repository).where(Repository.full_name == repo_full_name))
    repo = result.scalar_one_or_none()
    if not repo:
        return {"status": "skipped", "reason": "repo not connected"}

    if await _is_duplicate_delivery(db, delivery_id, event_type, repo.id):
        await db.commit()
        return {"status": "duplicate", "delivery_id": delivery_id}

    if event_type == "push":
        response_body = await _handle_push(payload, repo, db)
    elif event_type == "pull_request":
        response_body = await _handle_pull_request(payload, repo, db)
    else:
        await db.commit()  # still persist the delivery record even for ignored events
        return {"status": "ignored", "event": event_type}

    await db.commit()
    return response_body


async def _handle_push(payload: dict, repo: Repository, db: AsyncSession) -> dict:
    branch = payload.get("ref", "").replace("refs/heads/", "")
    commits_data = payload.get("commits", [])
    new_suggestions = 0

    # GitHub push webhook payloads only carry filenames (added/modified/removed),
    # never line-level diff content. To make the real diff/patch retrievable we
    # fetch it via the REST API using the repo owner's stored OAuth token —
    # best-effort: on any failure we fall back to the filename-only data above.
    gh: Optional[GitHubService] = None
    owner_result = await db.execute(select(Profile).where(Profile.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    if owner and owner.github_access_token:
        gh = GitHubService(owner.github_access_token)

    try:
        for commit_data in commits_data:
            sha = commit_data.get("id", "")
            if not sha:
                continue

            existing = await db.execute(
                select(Commit).where(Commit.repository_id == repo.id, Commit.sha == sha)
            )
            if existing.scalar_one_or_none():
                continue

            committed_raw = commit_data.get("timestamp", "")
            try:
                committed_at = datetime.fromisoformat(committed_raw.replace("Z", "+00:00"))
            except Exception:
                committed_at = datetime.now(timezone.utc)

            added = commit_data.get("added", [])
            modified = commit_data.get("modified", [])
            removed = commit_data.get("removed", [])
            all_files = [{"filename": f, "status": "added"} for f in added]
            all_files += [{"filename": f, "status": "modified"} for f in modified]
            all_files += [{"filename": f, "status": "removed"} for f in removed]
            additions = 0
            deletions = 0

            if gh:
                try:
                    detail = await gh.get_commit_detail(repo.full_name, sha)
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
            # Sessions here use autoflush=False, and commit.id is a
            # client-side default (uuid.uuid4) that SQLAlchemy only
            # populates on flush.
            await db.flush()

            tasks_result = await db.execute(
                select(Task).where(
                    Task.repository_id == repo.id,
                    Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
                    Task.parent_id.is_(None),
                )
            )
            open_tasks = tasks_result.scalars().all()
            tasks_plain = [{"id": str(t.id), "title": t.title, "status": t.status.value} for t in open_tasks]

            suggested = await analyze_activity(
                activity_type="commit",
                text_signals=[commit_data.get("message", "")],
                tasks=tasks_plain,
                event_key="push",
                changed_files=[f["filename"] for f in all_files],
                repo_status_mapping=repo.status_mapping,
            )

            for s in suggested:
                db.add(Suggestion(
                    repository_id=repo.id,
                    task_id=s["task_id"],
                    commit_id=commit.id,
                    action=SuggestionAction.STATUS_CHANGE,
                    proposed_status=s["proposed_status"],
                    explanation=s["explanation"],
                    confidence_score=s["confidence"],
                    evidence=s["evidence"],
                ))
                new_suggestions += 1

            commit.analyzed = True

            db.add(ActivityLog(
                repository_id=repo.id,
                event_type=ActivityType.COMMIT_RECEIVED,
                title=f"New commit: {sha[:7]} — {commit_data.get('message', '')[:60]}",
                description=f"{len(all_files)} files changed",
            ))
    finally:
        if gh:
            await gh.close()

    if new_suggestions > 0:
        db.add(ActivityLog(
            repository_id=repo.id,
            event_type=ActivityType.SUGGESTION_CREATED,
            title=f"AI created {new_suggestions} suggestion(s)",
            description="From push event",
        ))

    return {"status": "ok", "commits_processed": len(commits_data), "suggestions_created": new_suggestions}


async def _handle_pull_request(payload: dict, repo: Repository, db: AsyncSession) -> dict:
    action = payload.get("action", "")
    pr_data = payload.get("pull_request") or {}
    number = pr_data.get("number")
    if number is None:
        return {"status": "skipped", "reason": "no PR number"}
    if action not in _HANDLED_PR_ACTIONS:
        return {"status": "ignored", "action": action}

    merged = bool(pr_data.get("merged", False))
    state = PullRequestState.MERGED if merged else (
        PullRequestState.CLOSED if pr_data.get("state") == "closed" else PullRequestState.OPEN
    )

    def _parse_dt(raw: Optional[str]):
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None

    opened_at = _parse_dt(pr_data.get("created_at")) or datetime.now(timezone.utc)
    updated_at_github = _parse_dt(pr_data.get("updated_at"))
    closed_at = _parse_dt(pr_data.get("closed_at"))

    result = await db.execute(
        select(PullRequest).where(PullRequest.repository_id == repo.id, PullRequest.number == number)
    )
    pr = result.scalar_one_or_none()

    if pr is None:
        pr = PullRequest(
            repository_id=repo.id,
            number=number,
            title=pr_data.get("title", ""),
            body=pr_data.get("body") or None,
            author=(pr_data.get("user") or {}).get("login", ""),
            html_url=pr_data.get("html_url", ""),
            branch=(pr_data.get("head") or {}).get("ref", ""),
            base_branch=(pr_data.get("base") or {}).get("ref", ""),
            state=state,
            merged=merged,
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            changed_files=pr_data.get("changed_files", 0),
            opened_at=opened_at,
            updated_at_github=updated_at_github,
            closed_at=closed_at,
        )
        db.add(pr)
    else:
        pr.title = pr_data.get("title", pr.title)
        pr.body = pr_data.get("body") or pr.body
        pr.state = state
        pr.merged = merged
        pr.additions = pr_data.get("additions", pr.additions)
        pr.deletions = pr_data.get("deletions", pr.deletions)
        pr.changed_files = pr_data.get("changed_files", pr.changed_files)
        pr.updated_at_github = updated_at_github
        pr.closed_at = closed_at
        pr.analyzed = False  # something changed (new commits, or state transition) — re-analyze

    await db.flush()  # populate pr.id if newly created

    # Real per-file diff data (best-effort — the payload itself has none).
    owner_result = await db.execute(select(Profile).where(Profile.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    files_changed: list = []
    if owner and owner.github_access_token:
        gh = GitHubService(owner.github_access_token)
        try:
            raw_files = await gh.get_pr_files(repo.full_name, number)
            files_changed = [
                {
                    "filename": f.get("filename", ""),
                    "status": f.get("status", ""),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "patch": f.get("patch"),
                }
                for f in raw_files
            ]
            pr.files_changed = files_changed
        except Exception:
            pass
        finally:
            await gh.close()

    db.add(ActivityLog(
        repository_id=repo.id,
        event_type=ActivityType.PR_RECEIVED,
        title=f"PR #{number} {action}: {pr.title[:60]}",
        description=f"{pr.changed_files} files changed" if pr.changed_files else None,
    ))

    event_key = "pr_merged" if (action == "closed" and merged) else (
        "pr_closed" if action == "closed" else _EVENT_KEY_BY_PR_ACTION.get(action, "pr_opened")
    )

    tasks_result = await db.execute(
        select(Task).where(
            Task.repository_id == repo.id,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
            Task.parent_id.is_(None),
        )
    )
    open_tasks = tasks_result.scalars().all()
    tasks_plain = [{"id": str(t.id), "title": t.title, "status": t.status.value} for t in open_tasks]

    suggested = await analyze_activity(
        activity_type="pull_request",
        text_signals=[pr.title, pr.body or "", pr.branch],
        tasks=tasks_plain,
        event_key=event_key,
        changed_files=[f["filename"] for f in files_changed],
        repo_status_mapping=repo.status_mapping,
    )

    new_suggestions = 0
    for s in suggested:
        db.add(Suggestion(
            repository_id=repo.id,
            task_id=s["task_id"],
            pull_request_id=pr.id,
            action=SuggestionAction.STATUS_CHANGE,
            proposed_status=s["proposed_status"],
            explanation=s["explanation"],
            confidence_score=s["confidence"],
            evidence=s["evidence"],
        ))
        new_suggestions += 1

    pr.analyzed = True

    if new_suggestions:
        db.add(ActivityLog(
            repository_id=repo.id,
            event_type=ActivityType.SUGGESTION_CREATED,
            title=f"AI created {new_suggestions} suggestion(s) from PR #{number}",
            description=None,
        ))

    return {
        "status": "ok",
        "pr_number": number,
        "action": action,
        "suggestions_created": new_suggestions,
    }
