from fastapi import APIRouter
from app.api.v1 import auth
from app.api.v1 import soil
from app.api.v1 import report
from app.api.v1 import invoice
from app.api.v1 import farmers
from app.api.v1 import dashboard
from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(soil.router, prefix="/soil-tests", tags=["soil_test"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
api_router.include_router(invoice.router, prefix="/invoice", tags=["invoice"])
api_router.include_router(farmers.router, prefix="/farmers", tags=["farmers"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
