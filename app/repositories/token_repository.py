from uuid import UUID
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.models.download_token import DownloadToken

class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_token(self, token: DownloadToken) -> DownloadToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_token_by_string(self, token_str: str) -> Optional[DownloadToken]:
        stmt = select(DownloadToken).where(DownloadToken.token == token_str)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def increment_attempts(self, token_id: UUID) -> None:
        stmt = (
            update(DownloadToken)
            .where(DownloadToken.id == token_id)
            .values(attempts=DownloadToken.attempts + 1)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def mark_verified(self, token_id: UUID) -> None:
        stmt = (
            update(DownloadToken)
            .where(DownloadToken.id == token_id)
            .values(is_verified=True)
        )
        await self.session.execute(stmt)
        await self.session.commit()
