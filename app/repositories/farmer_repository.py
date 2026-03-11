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

    async def get_farmers_with_status(self, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> Tuple[List[dict], int]:
        try:
            # Import here to avoid circular dependency
            from app.models.soil_test import SoilTest
            from sqlalchemy import desc, or_

            # Base query for farmers
            count_stmt = select(func.count()).select_from(Farmer)
            stmt = select(
                Farmer,
                SoilTest.status.label("soil_test_status"),
                SoilTest.created_at.label("last_test_date")
            )

            # Apply search filter if provided
            if search:
                search_filter = or_(
                    Farmer.farmer_name.ilike(f"%{search}%"),
                    Farmer.whatsapp_number.ilike(f"%{search}%")
                )
                count_stmt = count_stmt.where(search_filter)
                stmt = stmt.where(search_filter)

            # Get total count with filter
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            # Subquery to get the latest soil test for each farmer
            latest_test_sub = select(
                SoilTest.farmer_id,
                func.max(SoilTest.id).label("latest_id")
            ).group_by(SoilTest.farmer_id).subquery()

            # Complete the join and ordering
            stmt = stmt.outerjoin(
                latest_test_sub, Farmer.id == latest_test_sub.c.farmer_id
            ).outerjoin(
                SoilTest, SoilTest.id == latest_test_sub.c.latest_id
            ).offset(skip).limit(limit).order_by(Farmer.created_at.desc())

            result = await self.session.execute(stmt)
            rows = result.all()

            farmers_list = []
            for row in rows:
                farmer_obj = row[0]
                status = row[1] if row[1] else "No Test Found"
                date = row[2]
                
                farmers_list.append({
                    "id": farmer_obj.id,
                    "farmer_name": farmer_obj.farmer_name,
                    "whatsapp_number": farmer_obj.whatsapp_number,
                    "address": farmer_obj.address,
                    "latest_soil_test_status": status,
                    "last_test_date": date
                })
            
            return farmers_list, total
        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching farmers with status: {str(e)}")
            raise DatabaseError("Failed to fetch farmers with status")
