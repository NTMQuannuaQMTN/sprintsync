"""Supabase JWT verification.

Identity and session issuance are entirely owned by Supabase Auth — this
app never mints its own tokens. The frontend authenticates via
supabase-js (GitHub OAuth) and attaches the resulting Supabase access
token as a Bearer token on every request; this module only verifies that
token was really issued by this project's Supabase instance and extracts
the user id (the JWT's `sub` claim, which equals auth.users.id /
profiles.id).

Verification is via Supabase's JWKS endpoint (asymmetric ES256/RS256), not
a shared HS256 secret — Supabase's current default for new projects signs
tokens with a private key it never exposes, and publishes only the public
half at /auth/v1/.well-known/jwks.json. A shared-secret HS256 approach
cannot verify these tokens at all, regardless of what value is configured;
it isn't a "wrong secret" problem, it's the wrong algorithm entirely.
Confirmed for this project by fetching its JWKS directly and seeing a real
`"alg": "ES256"` key, not an empty key set.
"""
import httpx
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

# Cached in memory for the life of the process. Refreshed once, automatically,
# whenever a token references a `kid` we haven't seen — that's what actually
# handles Supabase rotating its signing keys, not a time-based TTL.
_jwks_cache: dict | None = None


async def _fetch_jwks() -> dict:
    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        return resp.json()


async def _get_signing_key(kid: str | None) -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = await _fetch_jwks()

    key = next((k for k in _jwks_cache.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        # Might be a newly-rotated key we haven't cached yet — refresh once.
        _jwks_cache = await _fetch_jwks()
        key = next((k for k in _jwks_cache.get("keys", []) if k.get("kid") == kid), None)

    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown signing key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return key


async def decode_supabase_token(token: str) -> dict:
    if not settings.SUPABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured",
        )
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key = await _get_signing_key(header.get("kid"))

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "ES256")],
            audience="authenticated",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = await decode_supabase_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id
