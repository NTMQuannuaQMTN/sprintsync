"""Integration tests for the core V1 loop (tasks, webhook -> suggestion ->
approval -> activity log) against the real database. See conftest.py for
why JWT verification is bypassed via dependency override rather than a
forged token, and test_auth_integration.py for the equivalent on the auth
endpoints.
"""
import uuid


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
