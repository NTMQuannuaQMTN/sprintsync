"""Verifies approving a suggestion mirrors the status change to a
connected Notion integration (V2 Phase 7 wiring) — and that it stays a
harmless no-op when no integration is connected (the common case, already
covered incidentally by every other suggestion-approval test in this
suite passing unchanged).
"""
import uuid
from datetime import datetime, timezone

import asyncpg

from src.core.config import settings
from src.services.taskboard.notion import NotionBoardProvider


def _asyncpg_dsn() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _insert_pending_suggestion(repo_id, task_id, proposed_status="done"):
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    suggestion_id = uuid.uuid4()
    try:
        await conn.execute(
            """
            INSERT INTO suggestions
                (id, repository_id, task_id, status, action, proposed_status,
                 explanation, confidence_score, created_at, updated_at)
            VALUES ($1, $2, $3, 'pending', 'status_change', $4, 'test evidence', 0.9, $5, $5)
            """,
            suggestion_id, repo_id, task_id, proposed_status, datetime.now(timezone.utc),
        )
    finally:
        await conn.close()
    return suggestion_id


async def _ok_verify(self):
    return None


async def _noop_close(self):
    return None


async def test_approve_with_no_notion_connected_is_a_harmless_noop(client, test_repo):
    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks", json={"title": "Ship the release", "priority": "high"}
    )
    task_id = task_resp.json()["id"]
    suggestion_id = await _insert_pending_suggestion(test_repo, task_id)

    resp = await client.post(f"/api/v1/repositories/{test_repo}/suggestions/{suggestion_id}/approve")
    assert resp.status_code == 200

    task_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert task_after.json()["status"] == "done"


async def test_approve_mirrors_status_to_connected_notion_integration(client, test_repo, monkeypatch):
    monkeypatch.setattr(NotionBoardProvider, "verify_connection", _ok_verify)
    monkeypatch.setattr(NotionBoardProvider, "close", _noop_close)

    calls = {}

    async def _fake_find_task(self, query):
        calls["find_task_query"] = query
        return type("FakePage", (), {"id": "notion-page-1"})()

    async def _fake_update_status(self, task_id, status):
        calls["update_status"] = (task_id, status)
        return None

    monkeypatch.setattr(NotionBoardProvider, "find_task", _fake_find_task)
    monkeypatch.setattr(NotionBoardProvider, "update_status", _fake_update_status)

    await client.post(
        "/api/v1/integrations/notion/connect",
        json={"access_token": "tok", "database_id": "db-1"},
    )

    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks", json={"title": "Ship the release", "priority": "high"}
    )
    task_id = task_resp.json()["id"]
    suggestion_id = await _insert_pending_suggestion(test_repo, task_id, proposed_status="done")

    resp = await client.post(f"/api/v1/repositories/{test_repo}/suggestions/{suggestion_id}/approve")
    assert resp.status_code == 200

    assert calls["find_task_query"] == "Ship the release"
    assert calls["update_status"] == ("notion-page-1", "done")

    # Internal Task remains the source of truth regardless of the mirror.
    task_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert task_after.json()["status"] == "done"


async def test_approve_survives_notion_mirror_failure(client, test_repo, monkeypatch):
    """The internal approval must never be reverted or blocked by an
    external-board failure -- external APIs are unreliable by design."""
    monkeypatch.setattr(NotionBoardProvider, "verify_connection", _ok_verify)
    monkeypatch.setattr(NotionBoardProvider, "close", _noop_close)

    async def _raise(self, query):
        raise RuntimeError("Notion API is down")

    monkeypatch.setattr(NotionBoardProvider, "find_task", _raise)

    await client.post(
        "/api/v1/integrations/notion/connect",
        json={"access_token": "tok", "database_id": "db-1"},
    )

    task_resp = await client.post(
        f"/api/v1/repositories/{test_repo}/tasks", json={"title": "Ship the release", "priority": "high"}
    )
    task_id = task_resp.json()["id"]
    suggestion_id = await _insert_pending_suggestion(test_repo, task_id, proposed_status="done")

    resp = await client.post(f"/api/v1/repositories/{test_repo}/suggestions/{suggestion_id}/approve")
    assert resp.status_code == 200  # never surfaces the mirror failure to the caller

    task_after = await client.get(f"/api/v1/repositories/{test_repo}/tasks/{task_id}")
    assert task_after.json()["status"] == "done"  # internal approval still applied
