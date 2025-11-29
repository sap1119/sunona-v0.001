"""
User service for user management operations.
Handles registration, authentication, and profile management.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from datetime import datetime
from typing import Optional
import uuid

from database.models import User, Wallet
from services.auth import hash_password, verify_password, create_access_token, create_refresh_token


class UserService:
    """Service for user-related operations"""
    
    def create_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        company_name: Optional[str] = None,
        db: Session = None
    ) -> User:
        """
        Create new user account with wallet.
        Automatically creates a wallet for the user.
        """
        try:
            # Hash password
            password_hash = hash_password(password)
            
            # Create user
            user = User(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                company_name=company_name,
                role='user',
                is_active=True,
                email_verified=False
            )
            
            db.add(user)
            db.flush()  # Get user.id without committing
            
            # Create wallet for user
            wallet = Wallet(
                user_id=user.id,
                balance=0.0000,
                currency='USD'
            )
            
            db.add(wallet)
            db.commit()
            db.refresh(user)
            
            return user
            
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    def authenticate_user(self, email: str, password: str, db: Session) -> Optional[User]:
        """
        Authenticate user with email and password.
        Returns user if credentials are valid, None otherwise.
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        return user
    
    def login(self, email: str, password: str, db: Session) -> dict:
        """
        Login user and return tokens.
        """
        user = self.authenticate_user(email, password, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        access_token = create_access_token(
            data={"user_id": str(user.id), "email": user.email, "role": user.role}
        )
        refresh_token = create_refresh_token(
            data={"user_id": str(user.id), "email": user.email}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name
        }
    
    def get_user_by_id(self, user_id: str, db: Session) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str, db: Session) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        company_name: Optional[str] = None,
        phone: Optional[str] = None,
        avatar_url: Optional[str] = None,
        db: Session = None
    ) -> User:
        """
        Update user profile.
        User can only update their own profile (enforced by API layer).
        """
        user = self.get_user_by_id(user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if full_name is not None:
            user.full_name = full_name
        if company_name is not None:
            user.company_name = company_name
        if phone is not None:
            user.phone = phone
        if avatar_url is not None:
            user.avatar_url = avatar_url
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user
    
    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        db: Session
    ) -> bool:
        """Change user password"""
        user = self.get_user_by_id(user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return True
    
    def delete_user(self, user_id: str, db: Session) -> bool:
        """
        Delete user account and all associated data.
        Cascade deletes: wallet, transactions, agents, calls, etc.
        """
        user = self.get_user_by_id(user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db.delete(user)
        db.commit()
        
        return True


# Singleton instance
user_service = UserService()
