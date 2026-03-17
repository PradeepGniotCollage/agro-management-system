from fastapi import APIRouter, Depends, status, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import logging
from fastapi.responses import Response
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.soil_test import SoilTestCreate, SoilTestStartRequest, SoilTestResponse, SoilTestHistory
from app.repositories.soil_repository import SoilRepository
from app.repositories.farmer_repository import FarmerRepository
from app.repositories.user_repository import UserRepository
from app.services.soil_service import SoilService
from app.core.exceptions import SoilMonitoringError
from app.services.pdf_service import PDFService
from jose import jwt, JWTError
from app.models.device_heartbeat import DeviceHeartbeat

router = APIRouter()
logger = logging.getLogger(__name__)

async def _upsert_device_heartbeat(connected: bool, port: str | None, payload: dict | None) -> None:
    last_seen_at = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        hb = await session.get(DeviceHeartbeat, 1)
        if hb is None:
            hb = DeviceHeartbeat(id=1, connected=connected, port=port, payload=payload, last_seen_at=last_seen_at)
            session.add(hb)
        else:
            hb.connected = connected
            hb.port = port
            hb.payload = payload
            hb.last_seen_at = last_seen_at
            session.add(hb)
        await session.commit()

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
    request: Request,
    test_data: SoilTestStartRequest,
    x_device_key: str = Header(default="", alias="X-DEVICE-KEY"),
    soil_service: SoilService = Depends(get_soil_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Initialize a soil test record for a farmer.
    """
    user_id: int
    if x_device_key.strip() and settings.DEVICE_API_KEY and x_device_key.strip() == str(settings.DEVICE_API_KEY).strip():
        user_id = int(test_data.user_id or settings.DEVICE_USER_ID)
        if not test_data.sensor_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sensor_data is required for device submissions")
        await _upsert_device_heartbeat(True, None, test_data.sensor_data)
    else:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization or X-DEVICE-KEY")
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id_str: str = payload.get("sub")
            if user_id_str is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            user_id = int(user_id_str)
        except (JWTError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    try:
        if test_data.sensor_data:
            result = await soil_service.start_test_with_sensor_data(user_id, test_data, test_data.sensor_data)
        else:
            result = await soil_service.start_test(user_id, test_data)
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
    soil_service: SoilService = Depends(get_soil_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Checks if the soil sensors are physically connected and streaming data.
    """
    heartbeat = await db.get(DeviceHeartbeat, 1)
    now = datetime.now(timezone.utc)
    heartbeat_age_seconds = None
    if heartbeat is not None and heartbeat.last_seen_at:
        heartbeat_age_seconds = (now - heartbeat.last_seen_at).total_seconds()

    logger.info(
        f"Sensor status check: heartbeat={'present' if heartbeat is not None else 'missing'} "
        f"last_seen_at={getattr(heartbeat, 'last_seen_at', None)} age_seconds={heartbeat_age_seconds}"
    )

    if heartbeat_age_seconds is not None and heartbeat_age_seconds <= 300:
        logger.info("Sensor status source=heartbeat result=online")
        sensor_data = heartbeat.payload if isinstance(getattr(heartbeat, "payload", None), dict) else None
        data_available = bool(sensor_data)
        if not sensor_data:
            sensor_data = {
                "moisture": 0.0,
                "temperature": 0.0,
                "ph": 0.0,
                "ec": 0.0,
                "nitrogen": 0.0,
                "phosphorus": 0.0,
                "potassium": 0.0,
            }
        return {
            "connected": True,
            "status": "Online",
            "message": "Remote sensor is online (via device heartbeat).",
            "data": sensor_data,
            "last_seen_at": heartbeat.last_seen_at,
            "age_seconds": heartbeat_age_seconds,
            "data_available": data_available,
            "source": "heartbeat",
        }

    if settings.SERIAL_URL and "host.docker.internal" in settings.SERIAL_URL:
        logger.info("Sensor status source=heartbeat result=offline reason=no_recent_heartbeat remote_serial_unavailable")
        return {
            "connected": False,
            "status": "Offline",
            "message": "No recent device heartbeat. Run device_bridge.py on laptop to update status.",
            "data": None,
            "last_seen_at": heartbeat.last_seen_at if heartbeat is not None else None,
            "age_seconds": heartbeat_age_seconds,
            "source": "heartbeat",
        }

    status_info = await soil_service.check_sensor_connection()
    logger.info(f"Sensor status source=serial result={'online' if status_info.get('connected') else 'offline'}")

    return {
        "connected": status_info["connected"],
        "status": "Online" if status_info["connected"] else "Offline",
        "message": status_info["message"],
        "data": status_info["data"],
        "last_seen_at": heartbeat.last_seen_at if heartbeat is not None else None,
        "age_seconds": heartbeat_age_seconds,
        "source": "serial" if status_info.get("connected") else "serial_or_none",
    }

@router.post("/sensor-status", response_model=dict)
async def post_sensor_status(
    payload: dict,
    x_device_key: str = Header(default="", alias="X-DEVICE-KEY"),
    db: AsyncSession = Depends(get_db),
):
    if not settings.DEVICE_API_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DEVICE_API_KEY not configured")
    if x_device_key.strip() != str(settings.DEVICE_API_KEY).strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device key")

    connected = bool(payload.get("connected", True))
    port = payload.get("port")
    data = payload.get("data")
    last_seen_at = datetime.now(timezone.utc)

    hb = await db.get(DeviceHeartbeat, 1)
    if hb is None:
        hb = DeviceHeartbeat(id=1, connected=connected, port=port, payload=data, last_seen_at=last_seen_at)
        db.add(hb)
    else:
        hb.connected = connected
        hb.port = port
        hb.payload = data
        hb.last_seen_at = last_seen_at
        db.add(hb)

    await db.commit()
    return {"ok": True, "connected": connected, "last_seen_at": last_seen_at}

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
