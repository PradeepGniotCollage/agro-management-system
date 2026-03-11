from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import socket


class Settings(BaseSettings):
    PROJECT_NAME: str = "Jaiswal Khad Bhandar - Agro Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_PORT: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    DATABASE_URL: Optional[str] = None

    INITIAL_ADMIN_PHONE: str = "9838000000"
    INITIAL_ADMIN_PASSWORD: str = "1234"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    SERIAL_URL: Optional[str] = None
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# ---------- DATABASE URL NORMALIZATION & AUTO SWITCH ----------
if settings.DATABASE_URL:
    if settings.DATABASE_URL.startswith("postgres://"):
        settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif settings.DATABASE_URL.startswith("postgresql://"):
        settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    if all([settings.POSTGRES_USER, settings.POSTGRES_PASSWORD, settings.POSTGRES_PORT, settings.POSTGRES_DB]):
        host = settings.POSTGRES_SERVER or "localhost"
        try:
            socket.gethostbyname(host)
        except:
            host = "localhost"
        settings.DATABASE_URL = (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@{host}:"
            f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
        settings.SERIAL_URL = None
