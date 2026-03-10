from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class VerifyMobileRequest(BaseModel):
    mobile_number: str

class VerifyTokenResponse(BaseModel):
    farmer_name: str
    crop_type: str
    created_at: datetime
    soil_score: float

    model_config = {"from_attributes": True}
