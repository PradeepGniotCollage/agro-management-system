from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()

@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Checks if the API and database are reachable.
    """
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        db_status = "Online"
    except Exception as e:
        db_status = f"Offline: {str(e)}"

    return {
        "status": "Healthy" if db_status == "Online" else "Degraded",
        "api": "Online",
        "database": db_status
    }
