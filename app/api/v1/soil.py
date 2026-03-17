from fastapi import APIRouter, Depends, status, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import logging
from fastapi.responses import Response

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.soil_test import SoilTestCreate, SoilTestCreateWithSensorData, SoilTestIngestRequest, SoilTestResponse, SoilTestHistory
from app.repositories.soil_repository import SoilRepository
from app.repositories.farmer_repository import FarmerRepository
from app.services.soil_service import SoilService
from app.core.exceptions import SoilMonitoringError
from app.services.pdf_service import PDFService

router = APIRouter()
logger = logging.getLogger(__name__)

def get_soil_service(db: AsyncSession = Depends(get_db)):
    repo = SoilRepository(db)
    farmer_repo = FarmerRepository(db)
    return SoilService(repo, farmer_repo)

@router.get("/start", response_model=dict)
async def lookup_farmer_for_test(
    whatsapp_number: str,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service)
):
    """
    Lookup farmer details by WhatsApp number for real-time frontend suggestion.
    """
    if not soil_service.farmer_repository:
        raise HTTPException(status_code=500, detail="Farmer repository not configured")
        
    farmer = await soil_service.farmer_repository.get_by_whatsapp(whatsapp_number)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
        
    return {
        "farmer_name": farmer.farmer_name,
        "address": farmer.address,
        "whatsapp_number": farmer.whatsapp_number
    }

@router.post("/start", response_model=SoilTestResponse, status_code=status.HTTP_201_CREATED)
async def start_soil_test_workflow(
    test_data: SoilTestCreate,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Initialize a soil test record for a farmer.
    """
    try:
        result = await soil_service.start_test(current_user.id, test_data)
        await db.commit()
        return result
    except SoilMonitoringError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/start-manual", response_model=SoilTestResponse, status_code=status.HTTP_201_CREATED)
async def start_soil_test_manual(
    test_data: SoilTestCreateWithSensorData,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await soil_service.start_test_with_sensor_data(current_user.id, test_data, test_data.sensor_data)
        await db.commit()
        return result
    except SoilMonitoringError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/ingest", response_model=SoilTestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_soil_test(
    payload: SoilTestIngestRequest,
    x_device_key: str = Header(default="", alias="X-DEVICE-KEY"),
    soil_service: SoilService = Depends(get_soil_service),
    db: AsyncSession = Depends(get_db)
):
    if not settings.DEVICE_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DEVICE_API_KEY not configured")
    if x_device_key.strip() != str(settings.DEVICE_API_KEY).strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device key")

    user_id = payload.user_id or settings.DEVICE_USER_ID
    try:
        result = await soil_service.start_test_with_sensor_data(user_id, payload, payload.sensor_data)
        await db.commit()
        return result
    except SoilMonitoringError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))




@router.get("/user/{user_id}", response_model=List[SoilTestHistory])
async def get_user_reports(
    user_id: int,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service)
):
    """
    Get all soil reports for a specific user history.
    """
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized to view this user's history")
        
    return await soil_service.get_user_history(user_id)

@router.get("/farmer/{farmer_id}", response_model=List[SoilTestHistory])
async def get_farmer_reports(
    farmer_id: int,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service)
):
    """
    Get all soil reports for a specific farmer.
    """
    return await soil_service.get_farmer_history(farmer_id)

@router.get("/sensor-status", response_model=dict)
async def get_sensor_status(
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service)
):
    """
    Checks if the soil sensors are physically connected and streaming data.
    """
    status_info = await soil_service.check_sensor_connection()
    return {
        "connected": status_info["connected"],
        "status": "Online" if status_info["connected"] else "Offline",
        "message": status_info["message"],
        "data": status_info["data"]
    }

@router.get("/report/{test_id}")
async def download_report_pdf(
    test_id: int,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service)
):
    """
    Generates and downloads the PDF report for a soil test.
    """
    report_data = await soil_service.get_soil_test(test_id, current_user.id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    pdf_buffer = PDFService.generate_soil_report_pdf(report_data)
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Soil_Report_{test_id}.pdf"
        }
    )
