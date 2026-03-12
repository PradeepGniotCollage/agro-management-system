from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class SoilTestCreate(BaseModel):
    farmer_name: Optional[str] = None
    whatsapp_number: str
    address: Optional[str] = None
    crop_type: str

class MetaResponse(BaseModel):
    report_id: int
    farmer_id: Optional[int] = None
    created_at: datetime
    farmer_name: str
    whatsapp_number: str
    crop_type: str
    sensor_status: str
    status: str

class SummaryResponse(BaseModel):
    moisture: float
    temperature: float
    ph: float
    ec: float
    soil_score: float

class NutrientDetailResponse(BaseModel):
    name: str
    value: float
    unit: str
    ideal_range: str
    status: str


class FertilizerDetailResponse(BaseModel):
    name: str
    requirement: float
    unit: str

class SoilTestResponse(BaseModel):
    report_meta: MetaResponse
    summary: SummaryResponse
    primary_nutrients: List[NutrientDetailResponse]
    micronutrients: List[NutrientDetailResponse]
    environmental_parameters: List[NutrientDetailResponse]
    fertilizer_recommendation: List[FertilizerDetailResponse]
    summary_message: str

    model_config = {"from_attributes": True}

class SoilTestHistory(BaseModel):
    id: int
    user_id: int
    farmer_id: Optional[int] = None
    farmer_name: str
    crop_type: str
    soil_score: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
