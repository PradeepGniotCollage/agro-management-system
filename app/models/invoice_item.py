from sqlalchemy import Column, String, ForeignKey, Numeric, BigInteger, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(BigInteger, primary_key=True, index=True)
    invoice_id = Column(BigInteger, ForeignKey("invoices.id"), nullable=False, index=True)
    
    item_name = Column(String, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    rate = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
