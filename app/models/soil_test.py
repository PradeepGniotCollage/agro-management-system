from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.orm import relationship

from app.core.database import Base

class SoilTest(Base):
    __tablename__ = "soil_tests"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    farmer_id = Column(BigInteger, ForeignKey("farmers.id"), nullable=True, index=True)

    farmer_name = Column(String, nullable=False)
    whatsapp_number = Column(String, nullable=False)
    crop_type = Column(String, nullable=False)

    sensor_status = Column(String, default="Connected", nullable=False)
    status = Column(String, default="completed", nullable=False) # e.g., 'pending', 'processing', 'completed'

    # Sensor Input Data
    moisture = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    ph = Column(Float, nullable=False)
    ec = Column(Float, nullable=False)
    nitrogen = Column(Float, nullable=False)
    phosphorus = Column(Float, nullable=False)
    potassium = Column(Float, nullable=False)

    # AI Predicted Micronutrients
    zinc = Column(Float, nullable=False)
    boron = Column(Float, nullable=False)
    iron = Column(Float, nullable=False)
    copper = Column(Float, nullable=False)
    magnesium = Column(Float, nullable=False)
    manganese = Column(Float, nullable=False)
    calcium = Column(Float, nullable=False)
    sulphur = Column(Float, nullable=False)
    organic_carbon = Column(Float, nullable=False)

    # Computed Results
    soil_score = Column(Float, nullable=False)
    # JSON arrays of dicts for dynamically generated reports
    fertilizer_recommendation = Column(JSON, nullable=False, default=list)
    status_summary = Column(JSON, nullable=False, default=dict)
    summary_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", backref="soil_tests")
    download_tokens = relationship("DownloadToken", back_populates="soil_test", cascade="all, delete-orphan")
