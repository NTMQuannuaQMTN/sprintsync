"""Integration tests for V2 Phase 8's GitHub Action ingestion path — the
alternative to a GitHub-installed webhook, authenticated by a per-repo
bearer token instead of an HMAC signature. Real DB, same client/test_repo
fixtures as the other integration tests.
"""
import uuid

from sqlalchemy import select

from src.core.database import AsyncSessionLocal
from src.models.pull_request import PullRequest


def _push_payload(full_name: str) -> dict:
    return {
        "ref": "refs/heads/main",
        "repository": {"full_name": full_name},
        "commits": [
            {
                "id": "c" * 40,
                "message": "Implement Notion task board integration",
                "timestamp": "2026-08-25T09:00:00Z",
                "url": f"https://github.com/{full_name}/commit/{'c' * 40}",
                "author": {"name": "pytest", "email": "pytest@example.invalid"},
                "added": ["src/services/taskboard/notion.py"],
                "modified": [],
                "removed": [],
            }
        ],
    }


async def test_action_token_generation_and_rotation(client, test_repo):
    first = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    assert first.status_code == 200
    token_1 = first.json()["action_token"]
    assert len(token_1) > 20

    second = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    token_2 = second.json()["action_token"]
    assert token_2 != token_1  # rotation issues a new token, invalidating the old


async def test_action_endpoint_rejects_missing_token(client, test_repo):
    resp = await client.post(
        "/api/v1/webhook/action",
        json={"event_name": "push", "delivery_id": str(uuid.uuid4()), "payload": {}},
    )
    assert resp.status_code == 401


async def test_action_endpoint_rejects_invalid_token(client, test_repo):
    resp = await client.post(
        "/api/v1/webhook/action",
        json={"event_name": "push", "delivery_id": str(uuid.uuid4()), "payload": {}},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


async def test_action_endpoint_processes_push_event_with_valid_token(client, test_repo):
    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement Notion task board integration", "priority": "high"},
    )
    task_id = task_resp.json()["id"]

    token_resp = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    token = token_resp.json()["action_token"]

    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await client.post(
        "/api/v1/webhook/action",
        json={"event_name": "push", "delivery_id": str(uuid.uuid4()), "payload": _push_payload(full_name)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["suggestions_created"] >= 1

    suggestions = (
        await client.get(f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"})
    ).json()
    assert any(s["task_id"] == task_id for s in suggestions)


async def test_action_endpoint_rotated_token_no_longer_works(client, test_repo):
    first = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    old_token = first.json()["action_token"]
    await client.post(f"/api/v1/repositories/{test_repo}/action-token")  # rotate

    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await client.post(
        "/api/v1/webhook/action",
        json={"event_name": "push", "delivery_id": str(uuid.uuid4()), "payload": _push_payload(full_name)},
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert resp.status_code == 401


async def test_action_token_revocation(client, test_repo):
    token_resp = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    token = token_resp.json()["action_token"]

    revoke_resp = await client.delete(f"/api/v1/repositories/{test_repo}/action-token")
    assert revoke_resp.status_code == 204

    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await client.post(
        "/api/v1/webhook/action",
        json={"event_name": "push", "delivery_id": str(uuid.uuid4()), "payload": _push_payload(full_name)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_action_endpoint_duplicate_delivery_id_not_reprocessed(client, test_repo):
    token_resp = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    token = token_resp.json()["action_token"]
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]
    delivery_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"event_name": "push", "delivery_id": delivery_id, "payload": _push_payload(full_name)}

    first = await client.post("/api/v1/webhook/action", json=payload, headers=headers)
    assert first.json()["status"] == "ok"
    second = await client.post("/api/v1/webhook/action", json=payload, headers=headers)
    assert second.json() == {"status": "duplicate", "delivery_id": delivery_id}


async def test_action_endpoint_pull_request_event(client, test_repo):
    token_resp = await client.post(f"/api/v1/repositories/{test_repo}/action-token")
    token = token_resp.json()["action_token"]
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    pr_payload = {
        "action": "opened",
        "number": 3,
        "pull_request": {
            "number": 3,
            "title": "Add GitHub Action ingestion",
            "body": "",
            "user": {"login": "pytest-author"},
            "html_url": f"https://github.com/{full_name}/pull/3",
            "head": {"ref": "feature/gh-action"},
            "base": {"ref": "main"},
            "state": "open",
            "merged": False,
            "additions": 10,
            "deletions": 1,
            "changed_files": 1,
            "created_at": "2026-08-25T09:00:00Z",
            "updated_at": "2026-08-25T09:00:00Z",
            "closed_at": None,
        },
        "repository": {"full_name": full_name},
    }

    resp = await client.post(
        "/api/v1/webhook/action",
        json={"event_name": "pull_request", "delivery_id": str(uuid.uuid4()), "payload": pr_payload},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["action"] == "opened"

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PullRequest).where(PullRequest.repository_id == test_repo))
        assert result.scalar_one_or_none() is not None
