from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from urllib.parse import urlparse

from app.core.config import settings

_db_url = settings.DATABASE_URL or ""
_parsed = urlparse(_db_url)
_host = (_parsed.hostname or "").lower()
_is_pgbouncer = any(token in _host for token in ["pgbouncer", "pooler"])
_engine_kwargs = {"connect_args": {"statement_cache_size": 0}, "poolclass": NullPool} if _is_pgbouncer else {}

engine = create_async_engine(_db_url, echo=False, **_engine_kwargs)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
