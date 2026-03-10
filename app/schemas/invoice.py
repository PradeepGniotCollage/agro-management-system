from pydantic import BaseModel, Field, condecimal
from datetime import date
from typing import List, Optional

class InvoiceItemCreate(BaseModel):
    item_name: str = Field(..., min_length=1)
    # Require strictly positive quantity (cannot be negative or 0)
    quantity: condecimal(ge=0.01, max_digits=10, decimal_places=2) # type: ignore
    # Rate can be 0 but not negative
    rate: condecimal(ge=0, max_digits=10, decimal_places=2) # type: ignore

class InvoiceCreate(BaseModel):
    farmer_id: Optional[int] = None
    customer_name: str = Field(..., min_length=1)
    mobile_number: str = Field(..., min_length=10, max_length=15, pattern=r"^\d{10,15}$")
    address: str = Field(..., min_length=1)
    invoice_date: date

    items: List[InvoiceItemCreate] = Field(..., min_length=1)

class InvoiceMeta(BaseModel):
    invoice_number: str
    invoice_date: date
    farmer_id: Optional[int] = None
    customer_name: str
    mobile_number: str
    address: str

    class Config:
        from_attributes = True

class InvoiceItemResponse(BaseModel):
    item_name: str
    quantity: condecimal(max_digits=10, decimal_places=2) # type: ignore
    rate: condecimal(max_digits=10, decimal_places=2) # type: ignore
    total: condecimal(max_digits=12, decimal_places=2) # type: ignore

    class Config:
        from_attributes = True

class InvoiceResponse(BaseModel):
    id: int
    invoice_meta: InvoiceMeta
    items: List[InvoiceItemResponse]
    subtotal: condecimal(max_digits=10, decimal_places=2) # type: ignore
    grand_total: condecimal(max_digits=10, decimal_places=2) # type: ignore

    class Config:
        from_attributes = True
