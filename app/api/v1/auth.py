from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate, UserLogin, SignupResponse, Token, PasswordChange, ResetPassword
from app.core.database import get_db
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    """
    auth_service = AuthService(db)
    return await auth_service.signup(user_in)

from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login user and return JWT token. 
    Note: For Swagger UI, enter your numeric UserID in the 'username' field and PIN in 'password'.
    """
    # Support both numeric ID and phone number in the username field
    user_cred = UserLogin(user_id=form_data.username, pin=form_data.password)
        
    auth_service = AuthService(db)
    return await auth_service.login(user_cred)

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently logged in user details using the access token.
    """
    return current_user

@router.post("/change-password")
async def change_password(
    password_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for the currently authenticated user.
    """
    auth_service = AuthService(db)
    return await auth_service.change_password(current_user.id, password_in)

@router.post("/forgot-password")
async def forgot_password(
    reset_in: ResetPassword,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password by verifying email and phone number.
    Note: This is a simplified 'Forgot Password' flow using phone as 2FA.
    """
    auth_service = AuthService(db)
    return await auth_service.reset_password(reset_in)
