"""Profile Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProfileOut(BaseModel):
    id: uuid.UUID
    github_username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncProviderToken(BaseModel):
    """Sent once by the frontend right after a successful Supabase OAuth
    sign-in, so the backend can store the GitHub provider token for later
    GitHub API calls (listing repos, installing webhooks) — Supabase itself
    does not persist or refresh this token for us."""
    provider_token: str
