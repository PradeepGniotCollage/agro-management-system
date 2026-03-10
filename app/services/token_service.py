import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import HTTPException, status

from app.models.download_token import DownloadToken
from app.schemas.download_token import VerifyTokenResponse
from app.repositories.token_repository import TokenRepository
from app.repositories.soil_repository import SoilRepository

class TokenService:
    def __init__(self, token_repo: TokenRepository, soil_repo: SoilRepository):
        self.token_repo = token_repo
        self.soil_repo = soil_repo

    async def generate_token_for_report(self, soil_test_id: UUID) -> str:
        soil_test = await self.soil_repo.get_by_id(soil_test_id)
        if not soil_test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soil test not found")

        token_str = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        try:
            token = DownloadToken(
                token=token_str,
                soil_test_id=soil_test_id,
                expires_at=expires_at
            )
            await self.token_repo.create_token(token)
            return token_str
        except Exception as e:
            import logging
            logging.error(f"Database error during token creation: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create download token")

    async def get_valid_token_or_fail(self, token_str: str) -> DownloadToken:
        token = await self.token_repo.get_token_by_string(token_str)
        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        
        # Check expiry
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired")
            
        return token

    async def get_token_info(self, token_str: str) -> VerifyTokenResponse:
        token = await self.get_valid_token_or_fail(token_str)
        soil_test = await self.soil_repo.get_by_id(token.soil_test_id)
        
        if not soil_test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked soil test not found")

        return VerifyTokenResponse(
            farmer_name=soil_test.farmer_name,
            crop_type=soil_test.crop_type,
            created_at=soil_test.created_at,
            soil_score=soil_test.soil_score
        )

    async def verify_mobile(self, token_str: str, mobile_number: str) -> None:
        token = await self.get_valid_token_or_fail(token_str)
        
        if token.attempts >= 3:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Maximum verification attempts exceeded")
            
        soil_test = await self.soil_repo.get_by_id(token.soil_test_id)
        
        if not soil_test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked soil test not found")
            
        if soil_test.whatsapp_number == mobile_number:
            try:
                await self.token_repo.mark_verified(token.id)
            except Exception as e:
                import logging
                logging.error(f"Error marking token verified: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database save failed")
        else:
            try:
                await self.token_repo.increment_attempts(token.id)
            except Exception as e:
                import logging
                logging.error(f"Error incrementing token attempts: {e}")
            
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid mobile number")

    async def get_verified_soil_test_id(self, token_str: str) -> UUID:
        token = await self.get_valid_token_or_fail(token_str)
        if not token.is_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token not verified")
            
        return token.soil_test_id
