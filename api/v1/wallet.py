"""
Wallet API endpoints.
Handles wallet balance, transactions, and top-up operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from database.connection import get_db
from services.auth import get_current_user_id
from services.wallet_service import wallet_service

router = APIRouter(prefix="/api/v1/wallet", tags=["Wallet"])


# Response Models
class WalletResponse(BaseModel):
    id: str
    user_id: str
    balance: Decimal
    currency: str
    total_topped_up: Decimal
    total_spent: Decimal
    low_balance_threshold: Decimal
    auto_recharge_enabled: bool
    auto_recharge_amount: Optional[Decimal]

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: str
    reference_id: Optional[str]
    reference_type: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class AutoRechargeRequest(BaseModel):
    enabled: bool
    amount: Optional[Decimal] = None
    threshold: Optional[Decimal] = None


# Endpoints
@router.get("/", response_model=WalletResponse)
def get_my_wallet(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's wallet.
    User can only access their own wallet.
    """
    wallet = wallet_service.get_user_wallet(current_user_id, db)
    
    return WalletResponse(
        id=str(wallet.id),
        user_id=str(wallet.user_id),
        balance=wallet.balance,
        currency=wallet.currency,
        total_topped_up=wallet.total_topped_up,
        total_spent=wallet.total_spent,
        low_balance_threshold=wallet.low_balance_threshold,
        auto_recharge_enabled=wallet.auto_recharge_enabled,
        auto_recharge_amount=wallet.auto_recharge_amount
    )


@router.get("/balance")
def get_balance(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current wallet balance"""
    balance = wallet_service.get_balance(current_user_id, db)
    return {"balance": balance, "currency": "USD"}


@router.get("/transactions", response_model=List[TransactionResponse])
def get_my_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's transaction history.
    User can only access their own transactions.
    """
    transactions = wallet_service.get_transactions(current_user_id, limit, offset, db)
    
    return [
        TransactionResponse(
            id=str(t.id),
            type=t.type,
            amount=t.amount,
            balance_before=t.balance_before,
            balance_after=t.balance_after,
            description=t.description,
            reference_id=str(t.reference_id) if t.reference_id else None,
            reference_type=t.reference_type,
            created_at=t.created_at.isoformat()
        )
        for t in transactions
    ]


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get specific transaction.
    Verifies ownership before returning.
    """
    transaction = wallet_service.get_transaction_by_id(transaction_id, current_user_id, db)
    
    return TransactionResponse(
        id=str(transaction.id),
        type=transaction.type,
        amount=transaction.amount,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        description=transaction.description,
        reference_id=str(transaction.reference_id) if transaction.reference_id else None,
        reference_type=transaction.reference_type,
        created_at=transaction.created_at.isoformat()
    )


@router.put("/auto-recharge", response_model=WalletResponse)
def update_auto_recharge(
    request: AutoRechargeRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update auto-recharge settings"""
    wallet = wallet_service.update_auto_recharge(
        user_id=current_user_id,
        enabled=request.enabled,
        amount=request.amount,
        threshold=request.threshold,
        db=db
    )
    
    return WalletResponse(
        id=str(wallet.id),
        user_id=str(wallet.user_id),
        balance=wallet.balance,
        currency=wallet.currency,
        total_topped_up=wallet.total_topped_up,
        total_spent=wallet.total_spent,
        low_balance_threshold=wallet.low_balance_threshold,
        auto_recharge_enabled=wallet.auto_recharge_enabled,
        auto_recharge_amount=wallet.auto_recharge_amount
    )
