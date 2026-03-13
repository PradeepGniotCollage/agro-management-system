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

    # Pending Soil Tests (Farmers without a completed test, or tests that are not completed)
    # The requirement seems to be counting how many farmers still need their test done.
    # An easy way is: total_farmers - farmers_with_completed_tests
    completed_farmers_stmt = select(func.count(func.distinct(SoilTest.farmer_id))).where(
        SoilTest.status == "completed"
    )
    completed_farmers_count = (await db.execute(completed_farmers_stmt)).scalar() or 0
    pending_tests = farmers_count - completed_farmers_count
    if pending_tests < 0:
        pending_tests = 0

    # Completed Soil Tests
    completed_tests_stmt = select(func.count()).select_from(SoilTest).where(SoilTest.status == "completed")
    completed_tests = (await db.execute(completed_tests_stmt)).scalar() or 0
    
    return {
        "total_farmers": farmers_count,
        "pending_soil_tests": pending_tests,
        "completed_tests": completed_tests,
        "today_tests": today_tests
    }

@router.get("/farmer-stats")
async def get_farmer_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns specific farmer and test statistics:
    - total_registered_farmers
    - recent_farmers (registered in the last 30 days)
    - active_soil_tests (completed status)
    """
    # Total Registered Farmers
    total_farmers_stmt = select(func.count()).select_from(Farmer)
    total_farmers = (await db.execute(total_farmers_stmt)).scalar() or 0

    # Farmers Registered in the Last 30 Days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_farmers_stmt = select(func.count()).select_from(Farmer).where(Farmer.created_at >= thirty_days_ago)
    recent_farmers = (await db.execute(recent_farmers_stmt)).scalar() or 0

    # Active Soil Tests (Done/Completed)
    active_tests_stmt = select(func.count()).select_from(SoilTest).where(SoilTest.status == "completed")
    active_tests = (await db.execute(active_tests_stmt)).scalar() or 0

    return {
        "total_registered_farmers": total_farmers,
        "recent_farmers_last_30_days": recent_farmers,
        "active_soil_tests_completed": active_tests
    }
