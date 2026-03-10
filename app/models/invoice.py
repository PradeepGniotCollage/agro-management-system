from datetime import datetime, timezone, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Numeric, BigInteger, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(BigInteger, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    
    farmer_id = Column(BigInteger, ForeignKey("farmers.id"), nullable=True, index=True)
    customer_name = Column(String, nullable=False)
    mobile_number = Column(String, nullable=False)
    address = Column(String, nullable=False)
    invoice_date = Column(Date, nullable=False, default=date.today)
    
    subtotal = Column(Numeric(10, 2), nullable=False)
    grand_total = Column(Numeric(10, 2), nullable=False)
    
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    creator = relationship("User", backref="invoices")
    farmer = relationship("Farmer", backref="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
