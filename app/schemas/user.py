from typing import Optional, Union
from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid
from datetime import datetime

from app.utils.validators import validate_password_strength

class UserCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: Optional[EmailStr] = None
    phone: str = Field(..., max_length=15)
    role: str = Field(default="staff")

class UserLogin(BaseModel):
    user_id: Union[int, str]
    pin: str = Field(..., min_length=4, max_length=128)

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str

class SignupResponse(BaseModel):
    user_id: int
    pin: str
    message: str
    access_token: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    phone: str # Used for verification in lieu of OTP for now

class ResetPassword(BaseModel):
    email: EmailStr
    phone: str
    new_password: str

    new_password: str
