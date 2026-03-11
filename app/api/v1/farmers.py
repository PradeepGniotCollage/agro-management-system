from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.schemas.farmer import Farmer, FarmerCreate, FarmerUpdate, FarmerListResponse, FarmerStatusListResponse
from app.services.farmer_service import FarmerService
from app.repositories.farmer_repository import FarmerRepository

router = APIRouter()

def get_farmer_service(db: AsyncSession = Depends(get_db)):
    repo = FarmerRepository(db)
    return FarmerService(repo)


@router.get("/{farmer_id}", response_model=Farmer)
async def get_farmer(
    farmer_id: int,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    farmer = await farmer_service.get_farmer(farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@router.put("/{farmer_id}", response_model=Farmer)
async def update_farmer(
    farmer_id: int,
    farmer_in: FarmerUpdate,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    farmer = await farmer_service.update_farmer(farmer_id, farmer_in)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(
    farmer_id: int,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    if not await farmer_service.delete_farmer(farmer_id):
        raise HTTPException(status_code=404, detail="Farmer not found")
    return None

@router.get("/status-list", response_model=FarmerStatusListResponse)
async def get_farmers_with_status(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    farmers, total = await farmer_service.get_farmers_with_status(skip=skip, limit=limit)
    return {"farmers": farmers, "total": total}
