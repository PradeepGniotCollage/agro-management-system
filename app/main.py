from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.db_init import initialize_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    logger.info("Application starting up... Initializing database.")
    try:
        await initialize_db()
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
        raise
    
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
