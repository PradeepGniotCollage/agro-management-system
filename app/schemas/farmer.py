from typing import Optional, List
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

class FarmerBase(BaseModel):
    farmer_name: str
    whatsapp_number: str
    address: Optional[str] = None

class FarmerCreate(FarmerBase):
    pass

class FarmerUpdate(BaseModel):
    farmer_name: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None

class Farmer(FarmerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FarmerListResponse(BaseModel):
    farmers: List[Farmer]
    total: int

class FarmerWithStatus(BaseModel):
    id: int
    farmer_name: str
    whatsapp_number: str
    address: Optional[str] = None
    latest_soil_test_status: Optional[str] = "No Test Found"
    latest_soil_test_id: Optional[int] = None
    last_test_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

class FarmerStatusListResponse(BaseModel):
    farmers: List[FarmerWithStatus]
    pagination: PaginationMeta
