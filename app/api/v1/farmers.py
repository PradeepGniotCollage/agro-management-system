from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import io
import csv

from app.core.database import get_db
from app.api.deps import get_current_user
from app.schemas.farmer import Farmer, FarmerCreate, FarmerUpdate, FarmerListResponse, FarmerStatusListResponse
from app.services.farmer_service import FarmerService
from app.repositories.farmer_repository import FarmerRepository

router = APIRouter()

def get_farmer_service(db: AsyncSession = Depends(get_db)):
    repo = FarmerRepository(db)
    return FarmerService(repo)


@router.get("/lookup/{whatsapp_number}", response_model=Farmer)
async def lookup_farmer_by_whatsapp(
    whatsapp_number: str,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    """
    Lookup farmer details by WhatsApp number. Used by frontend for auto-fill suggestions.
    """
    farmer = await farmer_service.get_farmer_by_whatsapp(whatsapp_number)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer


@router.get("/status-list", response_model=FarmerStatusListResponse)
async def get_farmers_with_status(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    skip = (page - 1) * page_size
    farmers, total = await farmer_service.get_farmers_with_status(skip=skip, limit=page_size, search=search)
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "farmers": farmers,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@router.get("/export-csv")
async def export_farmers_csv(
    search: Optional[str] = None,
    current_user = Depends(get_current_user),
    farmer_service: FarmerService = Depends(get_farmer_service)
):
    # Fetch all farmers matching search (using a large limit for export)
    farmers, _ = await farmer_service.get_farmers_with_status(skip=0, limit=10000, search=search)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Farmer Name", "Mobile No.", "Address", "Soil Test Status", "Last Test Date"])
    
    # Data
    for farmer in farmers:
        last_test_date = farmer["last_test_date"].strftime("%Y-%m-%d %H:%M:%S") if farmer["last_test_date"] else "N/A"
        writer.writerow([
            farmer["farmer_name"],
            farmer["whatsapp_number"],
            farmer["address"] or "N/A",
            farmer["latest_soil_test_status"],
            last_test_date
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=farmers_status.csv"}
    )


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
