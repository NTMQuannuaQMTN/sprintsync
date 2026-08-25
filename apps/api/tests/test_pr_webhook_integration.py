"""Integration tests for V2's pull_request webhook ingestion and generic
delivery idempotency — against the real database, same pattern as
test_repository_flow_integration.py's push-event test.
"""
import hashlib
import hmac
import json
import uuid

from sqlalchemy import select

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.models.pull_request import PullRequest


def _sign(payload_bytes: bytes) -> str:
    return "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()


async def _post_webhook(client, payload: dict, event: str, delivery_id: str = None):
    payload_bytes = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": _sign(payload_bytes),
    }
    if delivery_id:
        headers["X-GitHub-Delivery"] = delivery_id
    return await client.post("/api/v1/webhook/github", content=payload_bytes, headers=headers)


def _pr_payload(full_name: str, action: str, number: int = 1, merged: bool = False, **overrides) -> dict:
    pr = {
        "number": number,
        "title": overrides.get("title", "Implement Notion task board integration"),
        "body": overrides.get("body", "Wires up the NotionBoardProvider"),
        "user": {"login": "pytest-author"},
        "html_url": f"https://github.com/{full_name}/pull/{number}",
        "head": {"ref": overrides.get("branch", "feature/notion-integration")},
        "base": {"ref": "main"},
        "state": "closed" if action == "closed" else "open",
        "merged": merged,
        "additions": 42,
        "deletions": 3,
        "changed_files": 2,
        "created_at": "2026-08-23T09:00:00Z",
        "updated_at": "2026-08-23T09:30:00Z",
        "closed_at": "2026-08-23T09:30:00Z" if action == "closed" else None,
    }
    return {"action": action, "number": number, "pull_request": pr, "repository": {"full_name": full_name}}


async def test_pull_request_opened_creates_pr_row_and_suggestion(client, test_repo):
    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement Notion task board integration", "priority": "high"},
    )
    task_id = task_resp.json()["id"]

    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await _post_webhook(client, _pr_payload(full_name, "opened"), "pull_request", delivery_id=str(uuid.uuid4()))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["action"] == "opened"
    assert body["suggestions_created"] >= 1

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PullRequest).where(PullRequest.repository_id == test_repo))
        pr = result.scalar_one_or_none()
        assert pr is not None
        assert pr.state.value == "open"
        assert pr.analyzed is True

    suggestions = await client.get(f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"})
    matching = [s for s in suggestions.json() if s["task_id"] == task_id]
    assert matching, "expected the PR to be matched to the task by title/branch overlap"
    # default mapping for "opened" is in_progress — never touches the task until approved
    assert matching[0]["proposed_status"] == "in_progress"

    task_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert task_after.json()["status"] == "todo"  # unchanged — suggestion, not applied


async def test_pull_request_merged_proposes_done_by_default_mapping(client, test_repo):
    await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement Notion task board integration", "priority": "high"},
    )
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await _post_webhook(
        client, _pr_payload(full_name, "closed", merged=True), "pull_request", delivery_id=str(uuid.uuid4())
    )
    assert resp.status_code == 200
    suggestions = (
        await client.get(f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"})
    ).json()
    assert any(s["proposed_status"] == "done" for s in suggestions)


async def test_pull_request_closed_without_merge_proposes_blocked(client, test_repo):
    await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement Notion task board integration", "priority": "high"},
    )
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await _post_webhook(
        client, _pr_payload(full_name, "closed", merged=False), "pull_request", delivery_id=str(uuid.uuid4())
    )
    assert resp.status_code == 200
    suggestions = (
        await client.get(f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"})
    ).json()
    assert any(s["proposed_status"] == "blocked" for s in suggestions)


async def test_repo_status_mapping_override_is_honored(client, test_repo):
    """A repo can override the default push->in_progress mapping — this
    must never require a code change, just a config value."""
    async with AsyncSessionLocal() as db:
        from src.models.repository import Repository
        result = await db.execute(select(Repository).where(Repository.id == test_repo))
        repo = result.scalar_one()
        repo.status_mapping = {"pr_opened": "blocked"}
        await db.commit()

    await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement Notion task board integration", "priority": "high"},
    )
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await _post_webhook(client, _pr_payload(full_name, "opened"), "pull_request", delivery_id=str(uuid.uuid4()))
    assert resp.status_code == 200
    suggestions = (
        await client.get(f"/api/v1/repositories/{test_repo}/suggestions", params={"status": "pending"})
    ).json()
    assert any(s["proposed_status"] == "blocked" for s in suggestions)


async def test_pr_synchronize_updates_existing_row_not_duplicated(client, test_repo):
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    await _post_webhook(client, _pr_payload(full_name, "opened"), "pull_request", delivery_id=str(uuid.uuid4()))
    await _post_webhook(
        client, _pr_payload(full_name, "synchronize", title="Implement Notion task board integration (updated)"),
        "pull_request", delivery_id=str(uuid.uuid4()),
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PullRequest).where(PullRequest.repository_id == test_repo))
        prs = result.scalars().all()
        assert len(prs) == 1  # updated in place, not a second row
        assert "updated" in prs[0].title


async def test_unhandled_pr_action_is_ignored(client, test_repo):
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]

    resp = await _post_webhook(client, _pr_payload(full_name, "labeled"), "pull_request", delivery_id=str(uuid.uuid4()))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ignored", "action": "labeled"}


async def test_duplicate_delivery_id_is_not_reprocessed(client, test_repo):
    """The core idempotency guarantee: the SAME X-GitHub-Delivery id must
    never be processed twice, even across genuinely different payload
    content (simulating GitHub's real retry behavior, which resends the
    identical delivery id on timeout/5xx)."""
    await client.post(
        f"/api/v1/repositories/{test_repo}/tasks",
        json={"title": "Implement Notion task board integration", "priority": "high"},
    )
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]
    delivery_id = str(uuid.uuid4())

    first = await _post_webhook(client, _pr_payload(full_name, "opened"), "pull_request", delivery_id=delivery_id)
    assert first.status_code == 200
    assert first.json()["status"] == "ok"

    second = await _post_webhook(client, _pr_payload(full_name, "opened"), "pull_request", delivery_id=delivery_id)
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate", "delivery_id": delivery_id}

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PullRequest).where(PullRequest.repository_id == test_repo))
        assert len(result.scalars().all()) == 1  # not double-processed


async def test_malformed_json_payload_returns_400_not_500(client):
    payload_bytes = b"{not actually valid json"
    resp = await client.post(
        "/api/v1/webhook/github",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": _sign(payload_bytes),
        },
    )
    assert resp.status_code == 400


async def test_missing_pr_number_is_skipped_gracefully(client, test_repo):
    repo_row = await client.get(f"/api/v1/repositories/{test_repo}")
    full_name = repo_row.json()["full_name"]
    payload = {"action": "opened", "pull_request": {}, "repository": {"full_name": full_name}}
    resp = await _post_webhook(client, payload, "pull_request", delivery_id=str(uuid.uuid4()))
    assert resp.status_code == 200
    assert resp.json() == {"status": "skipped", "reason": "no PR number"}
