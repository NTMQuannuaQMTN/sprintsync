"""Integration tests for V2 Phase 10 (project intelligence) — real DB,
same fixtures as the other integration tests. These exercise pure
DB-derived facts (stale tasks, unmatched activity, large-change outliers),
not AI reasoning.
"""
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

from src.core.config import settings


def _asyncpg_dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def test_stale_task_is_reported_after_cutoff(client, test_repo):
    resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Old untouched task", "priority": "medium"},
    )
    task_id = resp.json()["id"]

    old_ts = datetime.now(timezone.utc) - timedelta(days=20)
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    try:
        await conn.execute("UPDATE tasks SET updated_at = $1 WHERE id = $2", old_ts, uuid.UUID(task_id))
    finally:
        await conn.close()

    resp = await client.get(f"/api/v1/repositories/{test_repo}/intelligence")
    assert resp.status_code == 200
    stale = resp.json()["stale_tasks"]
    assert any(t["task_id"] == task_id for t in stale)
    matched = next(t for t in stale if t["task_id"] == task_id)
    assert matched["days_since_update"] >= 19


async def test_recently_updated_task_is_not_stale(client, test_repo):
    await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Fresh task", "priority": "medium"},
    )
    resp = await client.get(f"/api/v1/repositories/{test_repo}/intelligence")
    assert resp.status_code == 200
    assert resp.json()["stale_tasks"] == []


async def test_done_task_is_never_flagged_stale_even_if_old(client, test_repo):
    resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Old but done task", "priority": "medium"},
    )
    task_id = resp.json()["id"]
    await client.patch(f"/api/v1/repositories/{test_repo}/tasks/{task_id}", json={"status": "done"})

    old_ts = datetime.now(timezone.utc) - timedelta(days=60)
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    try:
        await conn.execute("UPDATE tasks SET updated_at = $1 WHERE id = $2", old_ts, uuid.UUID(task_id))
    finally:
        await conn.close()

    resp = await client.get(f"/api/v1/repositories/{test_repo}/intelligence")
    stale_ids = [t["task_id"] for t in resp.json()["stale_tasks"]]
    assert task_id not in stale_ids


async def test_analyzed_commit_with_no_suggestion_is_unmatched_activity(client, test_repo):
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    commit_id = uuid.uuid4()
    try:
        await conn.execute(
            """
            INSERT INTO commits
                (id, repository_id, sha, short_sha, message, author_name, author_email,
                 committed_at, html_url, branch, analyzed)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true)
            """,
            commit_id, test_repo, "a" * 40, "aaaaaaa", "Unrelated docs typo fix",
            "pytest", "pytest@example.invalid", datetime.now(timezone.utc),
            "https://github.com/x/y/commit/a", "main",
        )
    finally:
        await conn.close()

    resp = await client.get(f"/api/v1/repositories/{test_repo}/intelligence")
    assert resp.status_code == 200
    unmatched = resp.json()["unmatched_activity"]
    assert any(u["id"] == str(commit_id) and u["kind"] == "commit" for u in unmatched)


async def test_intelligence_requires_repo_ownership(client):
    resp = await client.get(f"/api/v1/repositories/{uuid.uuid4()}/intelligence")
    assert resp.status_code == 404
