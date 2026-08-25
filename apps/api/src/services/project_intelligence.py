"""Project intelligence (V2 Phase 10) — pure DB-derived observations about
a repository's task/activity state.

Nothing in this module involves an LLM or a confidence score. Every field
returned here is a directly observed fact computed from real rows already
in the database (a timestamp comparison, a count, an average of real
numbers) -- this is deliberately kept separate from services/ai_reasoning,
which infers and can be wrong. Callers (API responses, UI) must present
these as observed data, never as an AI opinion or a certainty about intent
-- e.g. "no activity in 19 days" is a fact; "this task is abandoned" would
be an inference this module does not make.
"""
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.commit import Commit
from src.models.pull_request import PullRequest
from src.models.suggestion import Suggestion
from src.models.task import Task, TaskStatus

STALE_TASK_DAYS = 14
UNMATCHED_ACTIVITY_WINDOW_DAYS = 30
LARGE_CHANGE_WINDOW_DAYS = 30
LARGE_CHANGE_MULTIPLIER = 3
LARGE_CHANGE_FLOOR_LINES = 100  # below this, "3x average" is noise on a quiet repo
_OPEN_STATUSES = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]


@dataclass
class StaleTask:
    task_id: str
    title: str
    status: str
    last_updated_at: datetime
    days_since_update: int


@dataclass
class UnmatchedActivity:
    kind: str  # "commit" | "pull_request"
    id: str
    identifier: str  # short sha, or "#123"
    summary: str
    occurred_at: datetime


@dataclass
class LargeChange:
    kind: str  # "commit" | "pull_request"
    id: str
    identifier: str
    summary: str
    lines_changed: int
    occurred_at: datetime


async def get_stale_tasks(db: AsyncSession, repository_id: UUID, days: int = STALE_TASK_DAYS) -> List[StaleTask]:
    """Open tasks (todo/in_progress/blocked) whose row hasn't changed in
    `days`. Task.updated_at moves whenever the task itself is edited or its
    status changes -- including via an approved Suggestion -- so this is a
    reasonable, if imperfect, proxy for "no recorded activity"."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Task)
        .where(
            Task.repository_id == repository_id,
            Task.status.in_(_OPEN_STATUSES),
            Task.parent_id.is_(None),
            Task.updated_at < cutoff,
        )
        .order_by(Task.updated_at.asc())
    )
    now = datetime.now(timezone.utc)
    return [
        StaleTask(
            task_id=str(t.id),
            title=t.title,
            status=t.status.value,
            last_updated_at=t.updated_at,
            days_since_update=(now - t.updated_at).days,
        )
        for t in result.scalars().all()
    ]


async def get_unmatched_activity(
    db: AsyncSession, repository_id: UUID, days: int = UNMATCHED_ACTIVITY_WINDOW_DAYS, limit: int = 20
) -> List[UnmatchedActivity]:
    """Commits/PRs that were analyzed (AI reasoning ran) but produced zero
    task matches -- development activity with no visible link to the task
    board. A repo with a lot of these either has an incomplete task list, or
    activity the task board doesn't know how to categorize; this module
    doesn't guess which."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    commit_result = await db.execute(
        select(Commit)
        .outerjoin(Suggestion, Suggestion.commit_id == Commit.id)
        .where(
            Commit.repository_id == repository_id,
            Commit.analyzed.is_(True),
            Commit.committed_at >= cutoff,
            Suggestion.id.is_(None),
        )
        .order_by(Commit.committed_at.desc())
        .limit(limit)
    )
    items = [
        UnmatchedActivity(
            kind="commit",
            id=str(c.id),
            identifier=c.short_sha,
            summary=c.message.splitlines()[0][:120] if c.message else "",
            occurred_at=c.committed_at,
        )
        for c in commit_result.scalars().all()
    ]

    pr_result = await db.execute(
        select(PullRequest)
        .outerjoin(Suggestion, Suggestion.pull_request_id == PullRequest.id)
        .where(
            PullRequest.repository_id == repository_id,
            PullRequest.analyzed.is_(True),
            PullRequest.opened_at >= cutoff,
            Suggestion.id.is_(None),
        )
        .order_by(PullRequest.opened_at.desc())
        .limit(limit)
    )
    items += [
        UnmatchedActivity(
            kind="pull_request",
            id=str(pr.id),
            identifier=f"#{pr.number}",
            summary=pr.title[:120],
            occurred_at=pr.opened_at,
        )
        for pr in pr_result.scalars().all()
    ]

    items.sort(key=lambda i: i.occurred_at, reverse=True)
    return items[:limit]


async def get_unusually_large_changes(
    db: AsyncSession, repository_id: UUID, days: int = LARGE_CHANGE_WINDOW_DAYS
) -> List[LargeChange]:
    """Recent commits/PRs whose total line count is well above this repo's
    own historical average -- a size outlier, not a judgment about whether
    the change was appropriate. Needs enough history to compute a meaningful
    average; returns nothing for a repo with too little data rather than
    guessing at a threshold."""
    commit_sizes_result = await db.execute(
        select(Commit.additions, Commit.deletions).where(Commit.repository_id == repository_id)
    )
    commit_sizes = [(a or 0) + (d or 0) for a, d in commit_sizes_result.all()]

    pr_sizes_result = await db.execute(
        select(PullRequest.additions, PullRequest.deletions).where(PullRequest.repository_id == repository_id)
    )
    pr_sizes = [(a or 0) + (d or 0) for a, d in pr_sizes_result.all()]

    all_sizes = [s for s in (commit_sizes + pr_sizes) if s > 0]
    if len(all_sizes) < 5:
        return []  # not enough history to call anything an outlier

    average = statistics.mean(all_sizes)
    threshold = max(average * LARGE_CHANGE_MULTIPLIER, LARGE_CHANGE_FLOOR_LINES)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: List[LargeChange] = []

    recent_commits = await db.execute(
        select(Commit).where(Commit.repository_id == repository_id, Commit.committed_at >= cutoff)
    )
    for c in recent_commits.scalars().all():
        total = (c.additions or 0) + (c.deletions or 0)
        if total >= threshold:
            out.append(LargeChange(
                kind="commit", id=str(c.id), identifier=c.short_sha,
                summary=c.message.splitlines()[0][:120] if c.message else "",
                lines_changed=total, occurred_at=c.committed_at,
            ))

    recent_prs = await db.execute(
        select(PullRequest).where(PullRequest.repository_id == repository_id, PullRequest.opened_at >= cutoff)
    )
    for pr in recent_prs.scalars().all():
        total = (pr.additions or 0) + (pr.deletions or 0)
        if total >= threshold:
            out.append(LargeChange(
                kind="pull_request", id=str(pr.id), identifier=f"#{pr.number}",
                summary=pr.title[:120], lines_changed=total, occurred_at=pr.opened_at,
            ))

    out.sort(key=lambda i: i.lines_changed, reverse=True)
    return out
