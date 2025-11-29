"""
Authentication API endpoints.
Handles user registration, login, and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from database.connection import get_db
from services.auth import get_current_user_id
from services.user_service import user_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# Request/Response Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str
    email: str
    full_name: Optional[str]


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    created_at: str

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Automatically creates a wallet for the user.
    """
    user = user_service.create_user(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        company_name=request.company_name,
        db=db
    )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat()
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns JWT access and refresh tokens.
    """
    result = user_service.login(request.email, request.password, db)
    return LoginResponse(**result)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's profile.
    User can only access their own profile.
    """
    user = user_service.get_user_by_id(current_user_id, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat()
    )


@router.put("/me", response_model=UserResponse)
def update_profile(
    request: UpdateProfileRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update authenticated user's profile.
    User can only update their own profile.
    """
    user = user_service.update_user(
        user_id=current_user_id,
        full_name=request.full_name,
        company_name=request.company_name,
        phone=request.phone,
        avatar_url=request.avatar_url,
        db=db
    )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat()
    )


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    Requires current password for verification.
    """
    user_service.change_password(
        user_id=current_user_id,
        current_password=request.current_password,
        new_password=request.new_password,
        db=db
    )
    
    return {"message": "Password changed successfully"}


@router.delete("/me")
def delete_account(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete user account and all associated data.
    This action cannot be undone.
    """
    user_service.delete_user(current_user_id, db)
    return {"message": "Account deleted successfully"}
