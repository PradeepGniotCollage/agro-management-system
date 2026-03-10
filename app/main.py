from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from contextlib import asynccontextmanager
import os
try:
    from app.core.config import settings
except Exception as _settings_err:
    class _FallbackSettings:
        PROJECT_NAME = "Jaiswal Khad Bhandar - Agro Management System"
        VERSION = "1.0.0"
        API_V1_STR = "/api/v1"
    settings = _FallbackSettings()
from app.api.v1.api import api_router
try:
    from app.core.db_init import initialize_db
except Exception as _dbinit_err:
    initialize_db = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database (serverless-safe)
    logger.info("Application starting up... (serverless-safe)")
    try:
        is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("ENVIRONMENT") == "production"
        if not is_serverless and initialize_db is not None:
            await initialize_db()
            logger.info("Database initialization complete.")
        else:
            logger.info("Skipping DB migrations/seeding at startup (serverless/production).")
    except Exception as e:
        logger.error(f"Startup DB init failed (skipped in serverless): {e}", exc_info=True)
    
    yield
    # Shutdown logic if needed
    logger.info("Application shutting down...")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} Time: {process_time:.4f}s")
    return response

from app.core.exceptions import SoilMonitoringError

# Centralized Exception Handler
@app.exception_handler(SoilMonitoringError)
async def soil_exception_handler(request: Request, exc: SoilMonitoringError):
    logger.error(f"Soil Monitoring Error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "status": "Error"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later.", "status": "InternalError"}
    )


app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
@limiter.limit("5/minute")
def root(request: Request):
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
