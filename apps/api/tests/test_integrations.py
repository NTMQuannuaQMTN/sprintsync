"""Integration tests for the Notion connect/list/disconnect endpoints
(V2 Phase 7 wiring) — real DB, with NotionBoardProvider's live-verification
call mocked at the class level (no real Notion token in this environment;
the request-shape itself is already covered by test_taskboard.py's
httpx.MockTransport tests).
"""
from src.services.taskboard.notion import NotionBoardProvider


async def _ok_verify(self):
    return None


async def _failing_verify(self):
    raise ValueError("401 unauthorized")


async def _noop_close(self):
    return None


async def test_connect_notion_succeeds_with_valid_credential(client, monkeypatch):
    monkeypatch.setattr(NotionBoardProvider, "verify_connection", _ok_verify)
    monkeypatch.setattr(NotionBoardProvider, "close", _noop_close)

    resp = await client.post(
        "/api/v1/integrations/notion/connect",
        json={
            "access_token": "secret_test_token",
            "database_id": "db-123",
            "workspace_name": "My Workspace",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["integration_type"] == "notion"
    assert body["workspace_name"] == "My Workspace"
    assert body["active"] is True
    assert "access_token" not in body


async def test_connect_notion_rejects_bad_credential_without_saving(client, monkeypatch):
    monkeypatch.setattr(NotionBoardProvider, "verify_connection", _failing_verify)
    monkeypatch.setattr(NotionBoardProvider, "close", _noop_close)

    resp = await client.post(
        "/api/v1/integrations/notion/connect",
        json={"access_token": "bad-token", "database_id": "db-123"},
    )
    assert resp.status_code == 400
    assert "unauthorized" in resp.json()["detail"].lower() or "verify" in resp.json()["detail"].lower()

    list_resp = await client.get("/api/v1/integrations")
    assert list_resp.json() == []


async def test_connect_notion_twice_updates_in_place_not_duplicated(client, monkeypatch):
    monkeypatch.setattr(NotionBoardProvider, "verify_connection", _ok_verify)
    monkeypatch.setattr(NotionBoardProvider, "close", _noop_close)

    await client.post(
        "/api/v1/integrations/notion/connect",
        json={"access_token": "token-1", "database_id": "db-1"},
    )
    await client.post(
        "/api/v1/integrations/notion/connect",
        json={"access_token": "token-2", "database_id": "db-2", "workspace_name": "Renamed"},
    )

    list_resp = await client.get("/api/v1/integrations")
    integrations = list_resp.json()
    assert len(integrations) == 1
    assert integrations[0]["workspace_name"] == "Renamed"


async def test_disconnect_notion(client, monkeypatch):
    monkeypatch.setattr(NotionBoardProvider, "verify_connection", _ok_verify)
    monkeypatch.setattr(NotionBoardProvider, "close", _noop_close)

    await client.post(
        "/api/v1/integrations/notion/connect",
        json={"access_token": "token-1", "database_id": "db-1"},
    )
    resp = await client.delete("/api/v1/integrations/notion")
    assert resp.status_code == 204

    list_resp = await client.get("/api/v1/integrations")
    assert list_resp.json()[0]["active"] is False


async def test_disconnect_notion_without_connection_is_404(client):
    resp = await client.delete("/api/v1/integrations/notion")
    assert resp.status_code == 404
