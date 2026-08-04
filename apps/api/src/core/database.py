"""Async SQLAlchemy database setup."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.core.config import settings

# Required when DATABASE_URL points at Supabase's Transaction Pooler
# (PgBouncer in transaction mode, port 6543) — as opposed to a direct
# connection or the Session Pooler. PgBouncer can hand a different physical
# backend connection to each transaction, which breaks named server-side
# prepared statements: SQLAlchemy's asyncpg dialect names and reuses them
# per pooled DBAPI connection, so a name can collide with (or vanish from)
# whatever backend PgBouncer happens to attach next
# ("prepared statement ... already exists" / "does not exist"). Three
# things are needed together, not just statement_cache_size=0 alone
# (confirmed by hitting the "already exists" variant even with that set):
#   - statement_cache_size=0: disable asyncpg's own client-side reuse cache
#   - prepared_statement_name_func=lambda: "": use unnamed statements, so
#     there's no name to collide across a swapped backend connection
#   - poolclass=NullPool: don't hold SQLAlchemy-level pooled connections
#     open across requests either, since PgBouncer already pools — a
#     long-lived pooled connection here is exactly what lets a stale
#     prepared-statement identity survive across a PgBouncer-swapped
#     backend in the first place.
# All three are no-ops against a direct/Session Pooler connection, so this
# is safe regardless of which DATABASE_URL points at.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: "",
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
