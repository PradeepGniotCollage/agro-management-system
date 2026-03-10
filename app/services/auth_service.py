from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate, UserLogin, SignupResponse, Token, PasswordChange, ResetPassword
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, get_password_hash
import uuid

class AuthService:
    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)

    async def signup(self, user_in: UserCreate) -> SignupResponse:
        import random
        import string
        
        # Check if phone exists
        if await self.repository.get_by_phone(user_in.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

        # Check if email exists
        if user_in.email and await self.repository.get_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered"
            )

        # Generate 4-digit PIN
        pin = ''.join(random.choices(string.digits, k=4))
        hashed_pin = get_password_hash(pin)

        # Create user
        user = await self.repository.create(user_in, hashed_pin)

        # Create access token
        access_token = create_access_token(subject=str(user.id))

        return SignupResponse(
            user_id=user.id,
            pin=pin,
            message="User created successfully. Please save your UserID and PIN.",
            access_token=access_token
        )

    async def login(self, user_in: UserLogin) -> Token:
        # Check if user_id is numeric or a phone number
        user = None
        try:
            numeric_id = int(user_in.user_id)
            user = await self.repository.get_by_id(numeric_id)
        except (ValueError, TypeError):
            pass
            
        if not user:
            user = await self.repository.get_by_phone(str(user_in.user_id))
        if not user or not verify_password(user_in.pin, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect UserID or PIN",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        access_token = create_access_token(subject=str(user.id))
        return Token(access_token=access_token, token_type="bearer")

    async def change_password(self, user_id: int, password_in: PasswordChange):
        user = await self.repository.get_by_id(user_id)
        if not user or not verify_password(password_in.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect old password"
            )
        
        if password_in.new_password != password_in.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
            
        await self.repository.update(user, {"hashed_password": get_password_hash(password_in.new_password)})
        return {"message": "Password changed successfully"}

    async def reset_password(self, reset_in: ResetPassword):
        user = await self.repository.get_by_email(reset_in.email)
        if not user or user.phone != reset_in.phone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid email or phone number"
            )
            
        await self.repository.update(user, {"hashed_password": get_password_hash(reset_in.new_password)})
        return {"message": "Password reset successfully"}
