from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db

__all__ = ['get_db_session']


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db():
        yield session
