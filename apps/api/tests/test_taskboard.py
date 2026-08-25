"""Tests for the V2 TaskBoardProvider abstraction.

InternalBoardProvider is tested against the real database (same fixture
pattern as the rest of this suite). NotionBoardProvider is tested against
httpx.MockTransport — this exercises the REAL request construction (URLs,
headers, JSON bodies) against fake responses shaped exactly like Notion's
real (freshly-verified-live, see notion.py's docstring) API, rather than
mocking at a higher level and only testing our own glue code.
"""
import json

import httpx
import pytest

from src.core.database import AsyncSessionLocal
from src.services.taskboard.internal import InternalBoardProvider
from src.services.taskboard.notion import NotionBoardProvider


# --- InternalBoardProvider (real DB) ---


async def test_internal_provider_create_find_update_comment_round_trip(test_repo):
    async with AsyncSessionLocal() as db:
        provider = InternalBoardProvider(db, test_repo)

        created = await provider.create_task("Implement Notion sync", "some description")
        assert created.status == "todo"

        found = await provider.find_task("Implement Notion sync")
        assert found is not None
        assert found.id == created.id

        fetched = await provider.get_task(created.id)
        assert fetched is not None
        assert fetched.title == "Implement Notion sync"

        updated = await provider.update_status(created.id, "done")
        assert updated.status == "done"

        await provider.add_comment(created.id, "Synced via SprintSync V2")

        tasks = await provider.list_tasks()
        assert any(t.id == created.id for t in tasks)

        await db.commit()


async def test_internal_provider_get_task_wrong_repo_returns_none(test_repo):
    async with AsyncSessionLocal() as db:
        provider = InternalBoardProvider(db, test_repo)
        created = await provider.create_task("Repo-scoped task")
        await db.commit()

    async with AsyncSessionLocal() as db2:
        import uuid
        other_provider = InternalBoardProvider(db2, uuid.uuid4())
        result = await other_provider.get_task(created.id)
        assert result is None


async def test_internal_provider_create_task_unsupported_is_not_thrown_here():
    """create_task IS supported on InternalBoardProvider (unlike a
    hypothetical read-only provider) — sanity check the base class default
    behavior separately, so a future read-only provider knows what to raise."""
    from src.services.taskboard.base import TaskBoardProvider

    class ReadOnlyProvider(TaskBoardProvider):
        async def find_task(self, query):
            return None

        async def get_task(self, task_id):
            return None

        async def update_status(self, task_id, status):
            raise NotImplementedError

        async def add_comment(self, task_id, comment):
            return None

    provider = ReadOnlyProvider()
    with pytest.raises(NotImplementedError):
        await provider.create_task("x")
    with pytest.raises(NotImplementedError):
        await provider.list_tasks()


# --- NotionBoardProvider (mocked transport) ---


def _notion_page(page_id="page-1", title="Implement Notion sync", status="In progress"):
    return {
        "id": page_id,
        "url": f"https://notion.so/{page_id}",
        "properties": {
            "Name": {"title": [{"plain_text": title}]},
            "Status": {"status": {"name": status}},
        },
    }


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _make_provider(handler) -> NotionBoardProvider:
    provider = NotionBoardProvider(token="secret_test_token", database_id="db-123")
    provider._client = httpx.AsyncClient(
        base_url="https://api.notion.com/v1",
        headers={
            "Authorization": "Bearer secret_test_token",
            "Notion-Version": "2026-03-11",
            "Content-Type": "application/json",
        },
        transport=_mock_transport(handler),
    )
    return provider


async def test_notion_find_task_sends_correct_query_and_parses_result():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/v1/databases/db-123":
            return httpx.Response(200, json={"data_sources": [{"id": "ds-1", "name": "Tasks"}]})
        if request.url.path == "/v1/data_sources/ds-1/query":
            body = json.loads(request.content)
            assert body["filter"] == {"property": "Name", "title": {"contains": "Notion sync"}}
            return httpx.Response(200, json={"results": [_notion_page()]})
        return httpx.Response(404)

    provider = _make_provider(handler)
    result = await provider.find_task("Notion sync")
    await provider.close()

    assert result is not None
    assert result.title == "Implement Notion sync"
    assert result.status == "In progress"
    assert result.id == "page-1"
    # data source id resolved via GET /databases/{id}, then used to query
    assert any(c.url.path == "/v1/databases/db-123" for c in calls)
    assert any(c.url.path == "/v1/data_sources/ds-1/query" for c in calls)


async def test_notion_data_source_id_is_cached_across_calls():
    database_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/databases/db-123":
            database_calls.append(request)
            return httpx.Response(200, json={"data_sources": [{"id": "ds-1", "name": "Tasks"}]})
        if request.url.path == "/v1/data_sources/ds-1/query":
            return httpx.Response(200, json={"results": []})
        return httpx.Response(404)

    provider = _make_provider(handler)
    await provider.find_task("a")
    await provider.find_task("b")
    await provider.close()

    assert len(database_calls) == 1  # resolved once, reused after


async def test_notion_update_status_sends_correct_patch_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == "/v1/pages/page-1"
        body = json.loads(request.content)
        assert body["properties"]["Status"]["status"]["name"] == "Done"
        return httpx.Response(200, json=_notion_page(status="Done"))

    provider = _make_provider(handler)
    result = await provider.update_status("page-1", "Done")
    await provider.close()
    assert result.status == "Done"


async def test_notion_add_comment_sends_correct_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/comments"
        body = json.loads(request.content)
        assert body["parent"] == {"page_id": "page-1"}
        assert body["rich_text"][0]["text"]["content"] == "hello from sprintsync"
        return httpx.Response(200, json={"id": "comment-1"})

    provider = _make_provider(handler)
    await provider.add_comment("page-1", "hello from sprintsync")
    await provider.close()


async def test_notion_create_task_parents_to_data_source_not_database():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/databases/db-123":
            return httpx.Response(200, json={"data_sources": [{"id": "ds-1", "name": "Tasks"}]})
        if request.url.path == "/v1/pages" and request.method == "POST":
            body = json.loads(request.content)
            assert body["parent"] == {"data_source_id": "ds-1"}
            return httpx.Response(200, json=_notion_page(title="New task"))
        return httpx.Response(404)

    provider = _make_provider(handler)
    result = await provider.create_task("New task")
    await provider.close()
    assert result.title == "New task"


async def test_notion_get_task_not_found_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"object": "error", "status": 404})

    provider = _make_provider(handler)
    result = await provider.get_task("nonexistent")
    await provider.close()
    assert result is None


async def test_notion_database_with_no_data_sources_raises_clear_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data_sources": []})

    provider = _make_provider(handler)
    with pytest.raises(ValueError, match="no data sources"):
        await provider.find_task("x")
    await provider.close()
