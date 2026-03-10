import logging
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.models.farmer import Farmer
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class FarmerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, farmer_data: dict) -> Farmer:
        try:
            db_farmer = Farmer(**farmer_data)
            self.session.add(db_farmer)
            await self.session.flush() # flush to get ID before commit if needed
            return db_farmer
        except SQLAlchemyError as e:
            logger.error(f"Database error during Farmer creation: {str(e)} | Data: {farmer_data}")
            raise DatabaseError(f"Failed to create farmer record: {str(e)}")

    async def get_by_id(self, farmer_id: int) -> Optional[Farmer]:
        try:
            stmt = select(Farmer).where(Farmer.id == farmer_id)
            result = await self.session.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching farmer {farmer_id}: {str(e)}")
            raise DatabaseError("Failed to fetch farmer record")

    async def get_by_whatsapp(self, whatsapp_number: str) -> Optional[Farmer]:
        try:
            stmt = select(Farmer).where(Farmer.whatsapp_number == whatsapp_number)
            result = await self.session.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching farmer by whatsapp {whatsapp_number}: {str(e)}")
            raise DatabaseError("Failed to fetch farmer record")

    async def get_multi(self, skip: int = 0, limit: int = 100) -> Tuple[List[Farmer], int]:
        try:
            # Get total count
            count_stmt = select(func.count()).select_from(Farmer)
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            # Get farmers
            stmt = select(Farmer).offset(skip).limit(limit).order_by(Farmer.created_at.desc())
            result = await self.session.execute(stmt)
            farmers = result.scalars().all()
            
            return farmers, total
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching farmers: {str(e)}")
            raise DatabaseError("Failed to fetch farmers list")

    async def update(self, farmer: Farmer, update_data: dict) -> Farmer:
        try:
            for key, value in update_data.items():
                setattr(farmer, key, value)
            self.session.add(farmer)
            return farmer
        except SQLAlchemyError as e:
            logger.error(f"Database error while updating farmer {farmer.id}: {str(e)}")
            raise DatabaseError("Failed to update farmer record")

    async def delete(self, farmer: Farmer) -> bool:
        try:
            await self.session.delete(farmer)
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error while deleting farmer {farmer.id}: {str(e)}")
            raise DatabaseError("Failed to delete farmer record")
