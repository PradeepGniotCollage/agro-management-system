from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, BigInteger, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base

class DownloadToken(Base):
    __tablename__ = "download_tokens"

    id = Column(BigInteger, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    soil_test_id = Column(BigInteger, ForeignKey("soil_tests.id"), nullable=False, index=True)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    soil_test = relationship("SoilTest", back_populates="download_tokens")
