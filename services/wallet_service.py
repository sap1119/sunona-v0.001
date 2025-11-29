"""
Wallet service for balance and transaction management.
Ensures user can only access their own wallet.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from database.models import Wallet, WalletTransaction, User


class WalletService:
    """Service for wallet operations with user isolation"""
    
    def get_user_wallet(self, user_id: str, db: Session) -> Wallet:
        """
        Get wallet for authenticated user.
        CRITICAL: Only returns wallet for the specified user_id.
        """
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return wallet
    
    def get_balance(self, user_id: str, db: Session) -> Decimal:
        """Get current wallet balance for user"""
        wallet = self.get_user_wallet(user_id, db)
        return wallet.balance
    
    def add_funds(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None,
        reference_type: str = "topup",
        db: Session = None
    ) -> WalletTransaction:
        """
        Add funds to user's wallet.
        Creates transaction record for audit trail.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive"
            )
        
        wallet = self.get_user_wallet(user_id, db)
        
        # Record balance before transaction
        balance_before = wallet.balance
        
        # Update wallet
        wallet.balance += amount
        wallet.total_topped_up += amount
        wallet.updated_at = datetime.utcnow()
        
        balance_after = wallet.balance
        
        # Create transaction record
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type="topup",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return transaction
    
    def deduct_funds(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None,
        reference_type: str = "call",
        db: Session = None
    ) -> WalletTransaction:
        """
        Deduct funds from user's wallet (for call costs).
        Prevents negative balance.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive"
            )
        
        wallet = self.get_user_wallet(user_id, db)
        
        # Check sufficient balance
        if wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient balance. Current: ${wallet.balance}, Required: ${amount}"
            )
        
        # Record balance before transaction
        balance_before = wallet.balance
        
        # Update wallet
        wallet.balance -= amount
        wallet.total_spent += amount
        wallet.updated_at = datetime.utcnow()
        
        balance_after = wallet.balance
        
        # Create transaction record
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type="deduction",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        # Check low balance alert
        if wallet.balance < wallet.low_balance_threshold:
            self._send_low_balance_alert(user_id, wallet.balance, db)
        
        return transaction
    
    def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        db: Session = None
    ) -> List[WalletTransaction]:
        """
        Get transaction history for user.
        CRITICAL: Only returns transactions for the specified user_id.
        """
        transactions = db.query(WalletTransaction)\\
            .filter(WalletTransaction.user_id == user_id)\\
            .order_by(WalletTransaction.created_at.desc())\\
            .limit(limit)\\
            .offset(offset)\\
            .all()
        
        return transactions
    
    def get_transaction_by_id(
        self,
        transaction_id: str,
        user_id: str,
        db: Session
    ) -> WalletTransaction:
        """
        Get specific transaction.
        CRITICAL: Verifies ownership before returning.
        """
        transaction = db.query(WalletTransaction).filter(
            WalletTransaction.id == transaction_id,
            WalletTransaction.user_id == user_id  # Ownership check
        ).first()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        return transaction
    
    def update_auto_recharge(
        self,
        user_id: str,
        enabled: bool,
        amount: Optional[Decimal] = None,
        threshold: Optional[Decimal] = None,
        db: Session = None
    ) -> Wallet:
        """Update auto-recharge settings"""
        wallet = self.get_user_wallet(user_id, db)
        
        wallet.auto_recharge_enabled = enabled
        if amount is not None:
            wallet.auto_recharge_amount = amount
        if threshold is not None:
            wallet.low_balance_threshold = threshold
        
        wallet.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(wallet)
        
        return wallet
    
    def _send_low_balance_alert(self, user_id: str, balance: Decimal, db: Session):
        """Send low balance alert to user (placeholder for email/notification)"""
        # TODO: Implement email/notification service
        print(f"⚠️  Low balance alert for user {user_id}: ${balance}")
        pass


# Singleton instance
wallet_service = WalletService()
