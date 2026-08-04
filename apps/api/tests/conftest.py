"""Shared fixtures for integration tests that hit the real database
DATABASE_URL points at (see .env) — as opposed to test_webhook_signature.py
/ test_ai_service.py / test_document_parser.py, which are pure unit tests
with no DB dependency.

Real Supabase-issued JWTs are ES256-signed with a private key only
Supabase holds, so tests can't forge one. Instead, these fixtures create a
real row in auth.users directly (exercising the real on_auth_user_created
trigger, the same as a genuine sign-in would) and override
get_current_user_id to return that user's id — the DB-facing logic under
test is real and unmocked; only the JWT-verification step is bypassed,
since that's Supabase's code, not ours, and already covered by BUG-012's
manual verification against this project's real JWKS.
"""
import uuid

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from src.core import security
from src.core.config import settings
from src.main import app


def _asyncpg_dsn() -> str:
    # asyncpg.connect() doesn't understand the "+asyncpg" SQLAlchemy dialect
    # marker in the URL scheme.
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture
async def test_user():
    """Creates a real auth.users row — triggering the real
    on_auth_user_created -> profiles trigger — against whatever database
    DATABASE_URL points at, and deletes it afterward (cascades to
    profiles/repositories/etc via the FK ON DELETE behavior defined in the
    migration)."""
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    user_id = uuid.uuid4()
    email = f"pytest-{user_id}@example.invalid"
    await conn.execute(
        "INSERT INTO auth.users (id, email, raw_user_meta_data) VALUES ($1, $2, $3::jsonb)",
        user_id,
        email,
        '{"user_name": "pytest-user", "avatar_url": "https://example.com/a.png"}',
    )
    try:
        yield user_id
    finally:
        await conn.execute("DELETE FROM auth.users WHERE id = $1", user_id)
        await conn.close()


@pytest.fixture
async def test_repo(test_user):
    """A real repositories row owned by test_user, bypassing the GitHub-API
    dependent connect flow (POST /repositories) since these tests aren't
    exercising GitHub itself. Deleting it cascades to tasks/commits/
    suggestions/specs/activity_logs via the FKs defined in the migration."""
    conn = await asyncpg.connect(_asyncpg_dsn(), statement_cache_size=0)
    repo_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO public.repositories
            (id, owner_id, github_repo_id, full_name, name, html_url)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        repo_id,
        test_user,
        # Random but stable-enough-for-a-test-run int; github_repo_id is
        # UNIQUE, so avoid colliding with a real connected repo.
        1_000_000_000 + int(str(uuid.uuid4().int)[:6]),
        f"pytest-org/{repo_id}",
        "pytest-repo",
        f"https://github.com/pytest-org/{repo_id}",
    )
    try:
        yield repo_id
    finally:
        await conn.execute("DELETE FROM public.repositories WHERE id = $1", repo_id)
        await conn.close()


@pytest.fixture
async def client(test_user):
    """An httpx client wired directly to the real ASGI app (no network
    hop), authenticated as `test_user` by overriding the JWT-verification
    dependency — everything after that (the route handler, the DB query)
    runs for real."""

    async def _override_user_id() -> str:
        return str(test_user)

    app.dependency_overrides[security.get_current_user_id] = _override_user_id
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
