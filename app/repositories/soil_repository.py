import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.soil_test import SoilTest
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class SoilRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, test_data: dict) -> SoilTest:
        try:
            db_soil_test = SoilTest(user_id=user_id, **test_data)
            self.session.add(db_soil_test)
            await self.session.commit()
            await self.session.refresh(db_soil_test)
            return db_soil_test
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error during SoilTest creation: {str(e)} | Data: {test_data}")
            raise DatabaseError(f"Failed to create soil test record: {str(e)}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Unexpected error during SoilTest creation: {str(e)}")
            raise DatabaseError("An unexpected error occurred while saving to database")

    async def get_by_id(self, test_id: int) -> Optional[SoilTest]:
        try:
            stmt = select(SoilTest).where(SoilTest.id == test_id)
            result = await self.session.execute(stmt)
            record = result.scalars().first()
            if record:
                logger.info(f"Successfully found soil test record: {record.id}")
            else:
                logger.info(f"No soil test record found in DB for ID: {test_id}")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching soil test {test_id}: {str(e)}")
            raise DatabaseError("Failed to fetch soil test record")

    async def get_all_by_user(self, user_id: int) -> List[SoilTest]:
        try:
            stmt = select(SoilTest).where(SoilTest.user_id == user_id).order_by(SoilTest.created_at.desc())
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching history for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to fetch user history")

    async def get_all_by_farmer(self, farmer_id: int) -> List[SoilTest]:
        try:
            stmt = select(SoilTest).where(SoilTest.farmer_id == farmer_id).order_by(SoilTest.created_at.desc())
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching history for farmer {farmer_id}: {str(e)}")
            raise DatabaseError("Failed to fetch farmer history")


    async def update(self, db_record: SoilTest, update_data: dict) -> SoilTest:
        try:
            for key, value in update_data.items():
                setattr(db_record, key, value)
            
            await self.session.commit()
            await self.session.refresh(db_record)
            return db_record
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error during SoilTest update: {str(e)} | ID: {db_record.id}")
            raise DatabaseError(f"Failed to update soil test record: {str(e)}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Unexpected error during SoilTest update: {str(e)}")
            raise DatabaseError("An unexpected error occurred while updating database")

