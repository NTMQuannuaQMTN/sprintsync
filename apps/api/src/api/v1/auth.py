"""Auth endpoints.

GitHub OAuth itself is entirely handled by Supabase Auth (configured in the
Supabase dashboard under Authentication > Providers > GitHub) — the
frontend calls supabase.auth.signInWithOAuth() directly and never talks to
this backend during the login flow itself. This module only:

1. Returns the current user's profile, given a valid Supabase access token.
2. Accepts the GitHub provider token once, right after sign-in, so this
   backend can call the GitHub API later (listing repos, installing
   webhooks) — Supabase returns that token to the client at sign-in time
   but does not persist or refresh it for us.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user_id
from src.models.profile import Profile
from src.schemas.profile import ProfileOut, SyncProviderToken, ProfileUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=ProfileOut)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the currently authenticated user's profile."""
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found — the auth.users -> profiles trigger may not have fired yet",
        )
    return profile


@router.post("/sync", response_model=ProfileOut)
async def sync_provider_token(
    body: SyncProviderToken,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Store the GitHub provider token for the current user.

    Call this once, right after supabase.auth.signInWithOAuth() resolves,
    passing session.provider_token from the Supabase client. Without this,
    GitHub-API-dependent endpoints (listing repos, installing webhooks)
    have no token to call GitHub with.
    """
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found — the auth.users -> profiles trigger may not have fired yet",
        )
    profile.github_access_token = body.provider_token
    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("/me", response_model=ProfileOut)
async def update_me(
    body: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Set the current user's display name.

    Used by the post-signup onboarding step: GitHub accounts frequently have
    no public display name, so the auth.users -> profiles trigger leaves
    `name` null and the frontend asks for it once, right after first
    sign-in.
    """
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found — the auth.users -> profiles trigger may not have fired yet",
        )
    profile.name = body.name.strip()
    await db.commit()
    await db.refresh(profile)
    return profile
