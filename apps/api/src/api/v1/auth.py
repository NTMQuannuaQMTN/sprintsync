"""GitHub OAuth authentication endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.config import settings
from src.core.database import get_db
from src.core.security import create_access_token, get_current_user_id
from src.models.user import User
from src.schemas.user import UserOut
from src.services.github import exchange_code_for_token, GitHubService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def github_login():
    """Redirect to GitHub OAuth authorization page."""
    scope = "read:user user:email repo"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope={scope}"
    )
    return RedirectResponse(url=url)


@router.get("/callback")
async def github_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Exchange GitHub OAuth code for JWT access token."""
    try:
        github_token = await exchange_code_for_token(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    gh = GitHubService(github_token)
    try:
        gh_user = await gh.get_authenticated_user()
    finally:
        await gh.close()

    # Upsert user
    result = await db.execute(select(User).where(User.github_id == gh_user["id"]))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            github_id=gh_user["id"],
            github_username=gh_user["login"],
            github_access_token=github_token,
            email=gh_user.get("email"),
            name=gh_user.get("name"),
            avatar_url=gh_user.get("avatar_url"),
            bio=gh_user.get("bio"),
        )
        db.add(user)
    else:
        user.github_access_token = github_token
        user.avatar_url = gh_user.get("avatar_url")
        user.name = gh_user.get("name")
        user.email = gh_user.get("email")

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(subject=str(user.id))

    # Redirect to frontend with token
    redirect_url = f"{settings.FRONTEND_URL}/dashboard?token={access_token}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/me", response_model=UserOut)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get currently authenticated user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
