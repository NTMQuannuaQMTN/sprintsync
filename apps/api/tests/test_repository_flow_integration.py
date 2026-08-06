"""Integration tests for the core V1 loop (tasks, webhook -> suggestion ->
approval -> activity log) against the real database. See conftest.py for
why JWT verification is bypassed via dependency override rather than a
forged token, and test_auth_integration.py for the equivalent on the auth
endpoints.
"""
import uuid
from datetime import datetime, timezone

import asyncpg

from src.core.config import settings


def _asyncpg_dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _insert_commit(repo_id, message: str) -> uuid.UUID:
    """Inserts a real, never-analyzed commit row directly — simulating one
    that arrived before the "Update to tasks" bulk-analyze endpoint existed
    (or before a webhook was installed), as opposed to test_webhook_creates_
    commit_and_suggestion_then_approve_flow below, which goes through the
    real webhook handler that analyzes+marks commits inline."""
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    commit_id = uuid.uuid4()
    sha = uuid.uuid4().hex
    try:
        await conn.execute(
            """
            INSERT INTO public.commits
                (id, repository_id, sha, short_sha, message, author_name,
                 author_email, committed_at, html_url, branch)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            commit_id,
            repo_id,
            sha,
            sha[:7],
            message,
            "pytest",
            "pytest@example.invalid",
            datetime.now(timezone.utc),
            f"https://github.com/pytest-org/{repo_id}/commit/{sha}",
            "main",
        )
    finally:
        await conn.close()
    return commit_id


async def test_create_list_update_task(client, test_repo):
    create = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement webhook signature verification", "priority": "high"},
    )
    assert create.status_code == 201
    task = create.json()
    assert task["title"] == "Implement webhook signature verification"
    assert task["status"] == "todo"

    listed = await client.get(f"/api/v1/repositories/{test_repo}/tasks")
    assert listed.status_code == 200
    assert any(t["id"] == task["id"] for t in listed.json())

    updated = await client.patch(
        f"/api/v1/repositories/{test_repo}/tasks/{task['id']}",
        json={"status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"


async def test_delete_task_removes_it_for_real(client, test_repo):
    create = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Task to be deleted", "priority": "low"},
    )
    task_id = create.json()["id"]

    deleted = await client.delete(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert deleted.status_code == 204

    # Really gone from the database, not just hidden.
    get_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert get_after.status_code == 404

    listed = await client.get(f"/api/v1/repositories/{test_repo}/tasks")
    assert all(t["id"] != task_id for t in listed.json())

    # Deleting the same task again is a 404, not a silent no-op or 500.
    delete_again = await client.delete(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert delete_again.status_code == 404


async def test_task_from_another_users_repo_is_not_visible(client, test_repo):
    """_assert_repo_owner should 404, not 403 or leak data, for a repo_id
    that exists but isn't owned by the authenticated user."""
    other_repo_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/repositories/{other_repo_id}/tasks")
    assert resp.status_code == 404


async def test_webhook_creates_commit_and_suggestion_then_approve_flow(client, test_repo):
    # A task whose title overlaps with the commit message below, so the AI
    # heuristic (src/services/ai.py) actually proposes a status change —
    # this is the real, unmocked heuristic, not a stub.
    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement webhook signature verification", "priority": "high"},
    )
    task_id = task_resp.json()["id"]

    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    payload = {
        "ref": "refs/heads/main",
        "repository": {"full_name": full_name},
        "commits": [
            {
                "id": "abc123def456abc123def456abc123def456ab1",
                "message": "Implement webhook signature verification",
                "timestamp": "2026-08-04T09:00:00Z",
                "url": f"https://github.com/{full_name}/commit/abc123",
                "author": {"name": "pytest", "email": "pytest@example.invalid"},
                "added": [],
                "modified": ["src/services/github.py"],
                "removed": [],
            }
        ],
    }
    webhook_resp = await client.post(
        "/api/v1/webhook/github",
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )
    assert webhook_resp.status_code == 200
    body = webhook_resp.json()
    assert body["commits_processed"] == 1
    assert body["suggestions_created"] >= 1

    suggestions = await client.get(
        f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"}
    )
    assert suggestions.status_code == 200
    matching = [s for s in suggestions.json() if s["task_id"] == task_id]
    assert matching, "expected a pending suggestion targeting the seeded task"
    suggestion = matching[0]
    assert suggestion["evidence"] is not None
    assert suggestion["confidence_score"] > 0
    # Guards the webhook.py fix that sets Suggestion.commit_id — without it
    # this enriched field silently stays null (see suggestions.py _enrich).
    assert suggestion["commit_sha"] is not None

    approve = await client.post(
        f"/api/v1/repositories/{test_repo}/suggestions/{suggestion['id']}/approve",
        json={"note": "looks right"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    task_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert task_after.json()["status"] == suggestion["proposed_status"]

    activity = await client.get(f"/api/v1/repositories/{test_repo}/activity")
    event_types = [a["event_type"] for a in activity.json()]
    assert "commit_received" in event_types
    assert "suggestion_created" in event_types
    assert "suggestion_approved" in event_types


async def test_update_to_tasks_button_analyzes_unanalyzed_commits(client, test_repo):
    """Exercises the "Update to tasks" button's backend: POST .../commits/
    analyze should pick up a real, never-analyzed commit row (simulating one
    that predates this feature, or arrived without a webhook), match it
    against a real open task via the same heuristic the webhook uses, and
    file a pending suggestion — without ever flipping the task's status
    itself (that still requires an explicit approve, per suggestions.py)."""
    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement rate limiting for the API", "priority": "high"},
    )
    task_id = task_resp.json()["id"]

    await _insert_commit(test_repo, "Implement rate limiting for the API")

    analyze = await client.post(f"/api/v1/repositories/{test_repo}/commits/analyze")
    assert analyze.status_code == 200, analyze.text
    body = analyze.json()
    assert body["commits_processed"] == 1
    assert body["suggestions_created"] >= 1

    suggestions = await client.get(
        f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"}
    )
    matching = [s for s in suggestions.json() if s["task_id"] == task_id]
    assert matching, "expected the bulk-analyze endpoint to suggest a status change"
    assert matching[0]["commit_sha"] is not None

    # Task status is untouched until a human approves — this endpoint only
    # ever creates suggestions, it never mutates tasks directly.
    task_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert task_after.json()["status"] == "todo"

    # Calling it again must not re-process the same (now-analyzed) commit —
    # otherwise every click of "Update to tasks" would duplicate suggestions.
    analyze_again = await client.post(f"/api/v1/repositories/{test_repo}/commits/analyze")
    assert analyze_again.json() == {"commits_processed": 0, "suggestions_created": 0}


async def test_list_commits_still_returns_locally_stored_commits_without_a_github_token(
    client, test_repo
):
    """GET /commits now also tries to backfill from the real GitHub API
    (_sync_commits_from_github in commits.py) — but test_repo's owning
    profile has no github_access_token (the trigger-created default), which
    is also the real-world state for most freshly-connected repos before a
    user's token round-trips through /auth/sync. That path must degrade to
    a no-op, not break the listing of whatever's already stored locally."""
    await _insert_commit(test_repo, "Existing commit stored before any sync")

    listed = await client.get(f"/api/v1/repositories/{test_repo}/commits")
    assert listed.status_code == 200
    messages = [c["message"] for c in listed.json()]
    assert "Existing commit stored before any sync" in messages
