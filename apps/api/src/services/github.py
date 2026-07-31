"""GitHub API service — OAuth, repositories, webhooks, commits."""
import hashlib
import hmac
from typing import Optional, List

import httpx

from src.core.config import settings


GITHUB_API_BASE = "https://api.github.com"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"


class GitHubService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def get_authenticated_user(self) -> dict:
        client = await self._get_client()
        resp = await client.get(f"{GITHUB_API_BASE}/user")
        resp.raise_for_status()
        return resp.json()

    async def list_repos(self, per_page: int = 100) -> List[dict]:
        client = await self._get_client()
        repos = []
        page = 1
        while True:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user/repos",
                params={"per_page": per_page, "page": page, "sort": "updated", "type": "owner"},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return repos

    async def get_repo(self, full_name: str) -> dict:
        client = await self._get_client()
        resp = await client.get(f"{GITHUB_API_BASE}/repos/{full_name}")
        resp.raise_for_status()
        return resp.json()

    async def get_commits(self, full_name: str, branch: str = "main", per_page: int = 20) -> List[dict]:
        client = await self._get_client()
        resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{full_name}/commits",
            params={"sha": branch, "per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_commit_detail(self, full_name: str, sha: str) -> dict:
        client = await self._get_client()
        resp = await client.get(f"{GITHUB_API_BASE}/repos/{full_name}/commits/{sha}")
        resp.raise_for_status()
        return resp.json()

    async def install_webhook(self, full_name: str, webhook_url: str) -> dict:
        client = await self._get_client()
        resp = await client.post(
            f"{GITHUB_API_BASE}/repos/{full_name}/hooks",
            json={
                "name": "web",
                "active": True,
                "events": ["push"],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": settings.GITHUB_WEBHOOK_SECRET,
                    "insecure_ssl": "0",
                },
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_webhook(self, full_name: str, hook_id: int) -> None:
        client = await self._get_client()
        resp = await client.delete(f"{GITHUB_API_BASE}/repos/{full_name}/hooks/{hook_id}")
        resp.raise_for_status()


async def exchange_code_for_token(code: str) -> str:
    """Exchange GitHub OAuth code for access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_OAUTH_TOKEN_URL,
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data['error_description']}")
        return data["access_token"]


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True  # skip in dev if not configured
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
