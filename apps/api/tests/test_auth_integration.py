"""Integration tests for the post-login flow against the real database.

Exercises exactly the sequence the frontend runs after a GitHub sign-in
(apps/web/src/app/auth/callback/page.tsx): fetch profile -> sync provider
token -> (if no name) set one via onboarding -> profile reflects it. Every
assertion here is checked against real rows in the real Postgres
DATABASE_URL points at — see conftest.py for why JWT verification itself
is bypassed rather than mocked-around.
"""


async def test_new_user_has_no_name_until_onboarding_sets_one(client, test_user):
    """This is the exact case apps/web/src/app/auth/callback/page.tsx
    branches on: `profile && !profile.name` -> /onboarding."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["id"] == str(test_user)
    assert profile["github_username"] == "pytest-user"
    assert profile["avatar_url"] == "https://example.com/a.png"
    # The on_auth_user_created trigger populated this row without a name —
    # this fixture's raw_user_meta_data has no full_name key, matching the
    # common real-world case of a GitHub account with no public name set.
    assert profile["name"] is None


async def test_onboarding_sets_name_and_it_sticks(client):
    resp = await client.patch("/api/v1/auth/me", json={"name": "  Ada Lovelace  "})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Ada Lovelace"  # trimmed, per ProfileUpdate

    # Simulates the callback page's logic re-checking after onboarding:
    # profile.name is now set, so it would route to /dashboard, not /onboarding.
    again = await client.get("/api/v1/auth/me")
    assert again.json()["name"] == "Ada Lovelace"


async def test_sync_provider_token_persists_it(client, test_user):
    resp = await client.post("/api/v1/auth/sync", json={"provider_token": "gho_faketoken_pytest"})
    assert resp.status_code == 200
    # github_access_token isn't in ProfileOut (never sent to the frontend),
    # so confirm it landed via a direct DB check instead of the API.
    import asyncpg

    from tests.conftest import _asyncpg_dsn

    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    try:
        token = await conn.fetchval(
            "SELECT github_access_token FROM public.profiles WHERE id = $1", test_user
        )
    finally:
        await conn.close()
    assert token == "gho_faketoken_pytest"


async def test_me_without_auth_override_is_rejected(test_user):
    """Sanity check that the dependency override in conftest.py is what's
    granting access — without it, the same app rejects the request, same
    as a real unauthenticated caller would get."""
    from httpx import ASGITransport, AsyncClient

    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/auth/me")
    assert resp.status_code == 401
