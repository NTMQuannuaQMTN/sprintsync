"""Integration tests for the new commit/PR/digest summary endpoints —
real DB, no ANTHROPIC_API_KEY in this environment so these exercise the
heuristic fallback path end-to-end through the real HTTP layer.
"""
import uuid
from datetime import datetime, timezone

import asyncpg

from src.core.config import settings


def _asyncpg_dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _insert_commit(repo_id, message="Fix the login bug for real this time"):
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    commit_id = uuid.uuid4()
    sha = uuid.uuid4().hex + uuid.uuid4().hex[:8]  # unique, still 40 hex chars
    try:
        await conn.execute(
            """
            INSERT INTO commits
                (id, repository_id, sha, short_sha, message, author_name, author_email,
                 committed_at, html_url, branch, analyzed)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true)
            """,
            commit_id, repo_id, sha, sha[:7], message,
            "pytest", "pytest@example.invalid", datetime.now(timezone.utc),
            f"https://github.com/x/y/commit/{sha}", "main",
        )
    finally:
        await conn.close()
    return commit_id


async def _insert_pr(repo_id, title="Add Notion integration", number=7):
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    pr_id = uuid.uuid4()
    try:
        await conn.execute(
            """
            INSERT INTO pull_requests
                (id, repository_id, number, title, body, author, html_url, branch, base_branch,
                 state, merged, opened_at, analyzed)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'open', false, $10, true)
            """,
            pr_id, repo_id, number, title, "Implements the provider", "pytest",
            f"https://github.com/x/y/pull/{number}", "feature/notion", "main",
            datetime.now(timezone.utc),
        )
    finally:
        await conn.close()
    return pr_id


async def test_commit_summary_endpoint_returns_heuristic_summary(client, test_repo):
    commit_id = await _insert_commit(test_repo)
    resp = await client.get(f"/api/v1/repositories/{test_repo}/commits/{commit_id}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "heuristic"
    assert "Fix the login bug" in body["summary"]


async def test_commit_summary_404_for_nonexistent_commit(client, test_repo):
    resp = await client.get(f"/api/v1/repositories/{test_repo}/commits/{uuid.uuid4()}/summary")
    assert resp.status_code == 404


async def test_pull_request_list_and_detail(client, test_repo):
    pr_id = await _insert_pr(test_repo)
    list_resp = await client.get(f"/api/v1/repositories/{test_repo}/pull_requests")
    assert list_resp.status_code == 200
    assert any(pr["id"] == str(pr_id) for pr in list_resp.json())

    detail_resp = await client.get(f"/api/v1/repositories/{test_repo}/pull_requests/{pr_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["title"] == "Add Notion integration"
    assert detail_resp.json()["state"] == "open"


async def test_pull_request_summary_endpoint(client, test_repo):
    pr_id = await _insert_pr(test_repo)
    resp = await client.get(f"/api/v1/repositories/{test_repo}/pull_requests/{pr_id}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "heuristic"
    assert "Add Notion integration" in body["summary"]


async def test_repository_digest_reflects_real_counts(client, test_repo):
    await _insert_commit(test_repo, message="First commit today")
    await _insert_commit(test_repo, message="Second commit today")

    resp = await client.get(f"/api/v1/repositories/{test_repo}/summary", params={"period": "day"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "heuristic"
    assert "2 commits" in body["summary"]


async def test_repository_digest_defaults_to_day_period(client, test_repo):
    resp = await client.get(f"/api/v1/repositories/{test_repo}/summary")
    assert resp.status_code == 200
    assert "today" in resp.json()["summary"]


async def test_repository_digest_week_period(client, test_repo):
    resp = await client.get(f"/api/v1/repositories/{test_repo}/summary", params={"period": "week"})
    assert resp.status_code == 200
    assert "this week" in resp.json()["summary"]
