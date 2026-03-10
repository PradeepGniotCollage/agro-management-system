from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.farmer import Farmer
from app.models.soil_test import SoilTest

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns dashboard statistics:
    - total_farmers
    - pending_soil_tests (assumed as records with no summary_message or specific flag)
    - completed_tests
    - today_tests
    """
    # Total Farmers
    farmers_count_stmt = select(func.count()).select_from(Farmer)
    farmers_count = (await db.execute(farmers_count_stmt)).scalar() or 0

    # Total Soil Tests
    total_tests_stmt = select(func.count()).select_from(SoilTest)
    total_tests = (await db.execute(total_tests_stmt)).scalar() or 0

    # Today's Tests
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_tests_stmt = select(func.count()).select_from(SoilTest).where(SoilTest.created_at >= today_start)
    today_tests = (await db.execute(today_tests_stmt)).scalar() or 0

    # Pending Soil Tests
    pending_tests_stmt = select(func.count()).select_from(SoilTest).where(SoilTest.status == "pending")
    pending_tests = (await db.execute(pending_tests_stmt)).scalar() or 0

    # Completed Soil Tests
    completed_tests_stmt = select(func.count()).select_from(SoilTest).where(SoilTest.status == "completed")
    completed_tests = (await db.execute(completed_tests_stmt)).scalar() or 0
    
    return {
        "total_farmers": farmers_count,
        "pending_soil_tests": pending_tests,
        "completed_tests": completed_tests,
        "today_tests": today_tests
    }
