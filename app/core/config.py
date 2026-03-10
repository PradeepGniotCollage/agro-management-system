from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import socket


class Settings(BaseSettings):
    PROJECT_NAME: str = "Jaiswal Khad Bhandar - Agro Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    DATABASE_URL: str

    INITIAL_ADMIN_PHONE: str = "9838000000"
    INITIAL_ADMIN_PASSWORD: str = "1234"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    SERIAL_URL: Optional[str] = None
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# ---------- AUTO SWITCH (Docker / Local) ----------
try:
    socket.gethostbyname(settings.POSTGRES_SERVER)
except:
    settings.POSTGRES_SERVER = "localhost"
    settings.DATABASE_URL = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@localhost:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    settings.SERIAL_URL = None