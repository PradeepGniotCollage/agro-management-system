from sqlalchemy import Column, DateTime, Boolean, String, BigInteger, JSON
from datetime import datetime, timezone

from app.core.database import Base


class DeviceHeartbeat(Base):
    __tablename__ = "device_heartbeats"

    id = Column(BigInteger, primary_key=True)
    connected = Column(Boolean, nullable=False, default=False)
    port = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
