import logging
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.farmer_repository import FarmerRepository
from app.schemas.farmer import FarmerCreate, FarmerUpdate
from app.models.farmer import Farmer

logger = logging.getLogger(__name__)

class FarmerService:
    def __init__(self, repository: FarmerRepository):
        self.repository = repository

    async def create_farmer(self, farmer_in: FarmerCreate) -> Farmer:
        return await self.repository.create(farmer_in.model_dump())

    async def get_farmer(self, farmer_id: int) -> Optional[Farmer]:
        return await self.repository.get_by_id(farmer_id)

    async def get_farmer_by_whatsapp(self, whatsapp_number: str) -> Optional[Farmer]:
        return await self.repository.get_by_whatsapp(whatsapp_number)

    async def get_farmers(self, skip: int = 0, limit: int = 100) -> Tuple[List[Farmer], int]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def update_farmer(self, farmer_id: int, farmer_in: FarmerUpdate) -> Optional[Farmer]:
        farmer = await self.repository.get_by_id(farmer_id)
        if not farmer:
            return None
        return await self.repository.update(farmer, farmer_in.model_dump(exclude_unset=True))

    async def delete_farmer(self, farmer_id: int) -> bool:
        farmer = await self.repository.get_by_id(farmer_id)
        if not farmer:
            return False
        return await self.repository.delete(farmer)

    async def get_farmers_with_status(self, skip: int = 0, limit: int = 100) -> Tuple[List[dict], int]:
        return await self.repository.get_farmers_with_status(skip=skip, limit=limit)
