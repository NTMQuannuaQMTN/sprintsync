"""NotionBoardProvider — real Notion API client.

Verified against Notion's current API docs (fetched live while writing
this, since Notion's API changed significantly since this codebase's
training-data cutoff — the old `/v1/databases/{id}/query` endpoint is
deprecated in favor of a `data_source_id`-scoped query, and page creation
now parents to a data source, not a database, directly):

  - GET  /v1/databases/{database_id}           -> resolve data_sources[]
  - POST /v1/data_sources/{data_source_id}/query
  - GET  /v1/pages/{page_id}
  - PATCH /v1/pages/{page_id}
  - POST /v1/comments
  - POST /v1/pages                             (parent: {"data_source_id": ...})

Notion-Version header: 2026-03-11 (current as of writing).

BLOCKED on a live NOTION_TOKEN for end-to-end verification in this
environment — see docs/V2_IMPLEMENTATION_PLAN.md. Endpoint shapes above
were confirmed against Notion's live documentation, not recalled from
training data, specifically because of the deprecation above.
"""
from typing import List, Optional

import httpx

from src.services.taskboard.base import TaskBoardProvider, TaskBoardTask

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"


class NotionBoardProvider(TaskBoardProvider):
    def __init__(
        self,
        token: str,
        database_id: str,
        title_property: str = "Name",
        status_property: str = "Status",
    ):
        self.token = token
        self.database_id = database_id
        self.title_property = title_property
        self.status_property = status_property
        self._client: Optional[httpx.AsyncClient] = None
        self._data_source_id: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=NOTION_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _get_data_source_id(self) -> str:
        """Databases now hold one or more "data sources" — queries and page
        creation target a data source, not the database directly. Uses the
        first data source, which covers the overwhelmingly common case (a
        database with a single, default data source); a database
        deliberately split across multiple data sources is out of scope."""
        if self._data_source_id:
            return self._data_source_id
        client = await self._get_client()
        resp = await client.get(f"/databases/{self.database_id}")
        resp.raise_for_status()
        data_sources = resp.json().get("data_sources", [])
        if not data_sources:
            raise ValueError(f"Notion database {self.database_id} has no data sources")
        self._data_source_id = data_sources[0]["id"]
        return self._data_source_id

    async def verify_connection(self) -> None:
        """Real network call confirming the token can resolve the
        configured database — raises on failure (bad token, wrong
        database_id, no data sources). Used at connect time
        (api/v1/integrations.py) so a bad credential fails loudly
        immediately rather than silently at the next suggestion approval."""
        await self._get_data_source_id()

    async def find_task(self, query: str) -> Optional[TaskBoardTask]:
        client = await self._get_client()
        data_source_id = await self._get_data_source_id()
        resp = await client.post(
            f"/data_sources/{data_source_id}/query",
            json={
                "filter": {"property": self.title_property, "title": {"contains": query}},
                "page_size": 1,
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return self._to_task(results[0]) if results else None

    async def get_task(self, task_id: str) -> Optional[TaskBoardTask]:
        client = await self._get_client()
        resp = await client.get(f"/pages/{task_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._to_task(resp.json())

    async def update_status(self, task_id: str, status: str) -> TaskBoardTask:
        client = await self._get_client()
        resp = await client.patch(
            f"/pages/{task_id}",
            json={"properties": {self.status_property: {"status": {"name": status}}}},
        )
        resp.raise_for_status()
        return self._to_task(resp.json())

    async def add_comment(self, task_id: str, comment: str) -> None:
        client = await self._get_client()
        resp = await client.post(
            "/comments",
            json={
                "parent": {"page_id": task_id},
                "rich_text": [{"type": "text", "text": {"content": comment}}],
            },
        )
        resp.raise_for_status()

    async def list_tasks(self) -> List[TaskBoardTask]:
        client = await self._get_client()
        data_source_id = await self._get_data_source_id()
        resp = await client.post(f"/data_sources/{data_source_id}/query", json={"page_size": 100})
        resp.raise_for_status()
        return [self._to_task(r) for r in resp.json().get("results", [])]

    async def create_task(self, title: str, description: str = "") -> TaskBoardTask:
        client = await self._get_client()
        data_source_id = await self._get_data_source_id()
        properties = {self.title_property: {"title": [{"text": {"content": title}}]}}
        resp = await client.post(
            "/pages",
            json={"parent": {"data_source_id": data_source_id}, "properties": properties},
        )
        resp.raise_for_status()
        return self._to_task(resp.json())

    def _to_task(self, page: dict) -> TaskBoardTask:
        props = page.get("properties", {})
        title_prop = props.get(self.title_property, {})
        title = "".join(t.get("plain_text", "") for t in title_prop.get("title", [])) or "(untitled)"
        status_prop = props.get(self.status_property, {})
        status = (status_prop.get("status") or {}).get("name")
        return TaskBoardTask(id=page["id"], title=title, status=status, url=page.get("url"), raw=page)
