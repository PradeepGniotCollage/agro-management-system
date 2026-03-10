from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, BigInteger

from app.core.database import Base

class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(BigInteger, primary_key=True, index=True)
    farmer_name = Column(String, nullable=False)
    whatsapp_number = Column(String, nullable=False, unique=True, index=True)
    address = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
