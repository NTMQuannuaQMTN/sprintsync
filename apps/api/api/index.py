"""Vercel serverless entrypoint.

Vercel's Python runtime looks for an ASGI/WSGI `app` under an `api/`
directory relative to the project's Root Directory (apps/api). This just
re-exports the real FastAPI app so Vercel can find it — local dev and any
other host (Render, Railway, etc.) keep running `src.main:app` directly via
uvicorn, unaffected by this file.
"""
from src.main import app  # noqa: F401
