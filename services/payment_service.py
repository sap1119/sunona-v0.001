"""
Payment service for Stripe integration and top-up processing.
Handles payment processing, webhooks, and payment history.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import stripe
import os

from database.models import TopUpPayment, Wallet
from services.wallet_service import wallet_service

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")


class PaymentService:
    """Service for payment processing"""
    
    def create_payment_intent(
        self,
        user_id: str,
        amount: Decimal,
        currency: str = "usd",
        db: Session = None
    ) -> dict:
        """
        Create Stripe payment intent for top-up.
        Returns client_secret for frontend.
        """
        # Get user's wallet
        wallet = wallet_service.get_user_wallet(user_id, db)
        
        # Create payment record
        payment = TopUpPayment(
            user_id=user_id,
            wallet_id=wallet.id,
            amount=amount,
            currency=currency.upper(),
            status="pending",
            payment_method="card"
        )
        
        db.add(payment)
        db.flush()
        
        try:
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                metadata={
                    "user_id": str(user_id),
                    "payment_id": str(payment.id),
                    "wallet_id": str(wallet.id)
                }
            )
            
            # Update payment record
            payment.stripe_payment_intent_id = intent.id
            db.commit()
            db.refresh(payment)
            
            return {
                "payment_id": str(payment.id),
                "client_secret": intent.client_secret,
                "amount": amount,
                "currency": currency
            }
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment error: {str(e)}"
            )
    
    def handle_payment_success(
        self,
        payment_intent_id: str,
        db: Session
    ) -> TopUpPayment:
        """
        Handle successful payment.
        Adds funds to wallet.
        """
        # Find payment record
        payment = db.query(TopUpPayment).filter(
            TopUpPayment.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        if payment.status == "succeeded":
            return payment  # Already processed
        
        # Update payment status
        payment.status = "succeeded"
        payment.paid_at = datetime.utcnow()
        
        # Add funds to wallet
        wallet_service.add_funds(
            user_id=str(payment.user_id),
            amount=payment.amount,
            description=f"Top-up via Stripe - ${payment.amount}",
            reference_id=str(payment.id),
            reference_type="payment",
            db=db
        )
        
        db.commit()
        db.refresh(payment)
        
        return payment
    
    def handle_payment_failure(
        self,
        payment_intent_id: str,
        db: Session
    ) -> TopUpPayment:
        """Handle failed payment"""
        payment = db.query(TopUpPayment).filter(
            TopUpPayment.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if payment:
            payment.status = "failed"
            db.commit()
            db.refresh(payment)
        
        return payment
    
    def get_user_payments(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        db: Session = None
    ) -> List[TopUpPayment]:
        """
        Get user's payment history.
        CRITICAL: Only returns payments for the specified user_id.
        """
        payments = db.query(TopUpPayment)\\
            .filter(TopUpPayment.user_id == user_id)\\
            .order_by(TopUpPayment.created_at.desc())\\
            .limit(limit)\\
            .offset(offset)\\
            .all()
        
        return payments
    
    def get_payment_by_id(
        self,
        payment_id: str,
        user_id: str,
        db: Session
    ) -> TopUpPayment:
        """
        Get specific payment.
        CRITICAL: Verifies ownership before returning.
        """
        payment = db.query(TopUpPayment).filter(
            TopUpPayment.id == payment_id,
            TopUpPayment.user_id == user_id  # Ownership check
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        return payment


# Singleton instance
payment_service = PaymentService()
