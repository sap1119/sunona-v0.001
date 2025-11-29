"""
Payment API endpoints.
Handles top-up payments and payment history.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from decimal import Decimal

from database.connection import get_db
from services.auth import get_current_user_id
from services.payment_service import payment_service

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


# Request/Response Models
class CreatePaymentRequest(BaseModel):
    amount: Decimal
    currency: str = "usd"


class PaymentResponse(BaseModel):
    id: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str
    paid_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# Endpoints
@router.post("/create-intent")
def create_payment_intent(
    request: CreatePaymentRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create Stripe payment intent for top-up.
    Returns client_secret for frontend.
    """
    result = payment_service.create_payment_intent(
        user_id=current_user_id,
        amount=request.amount,
        currency=request.currency,
        db=db
    )
    
    return result


@router.get("/", response_model=List[PaymentResponse])
def get_my_payments(
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's payment history.
    User can only access their own payments.
    """
    payments = payment_service.get_user_payments(current_user_id, limit, offset, db)
    
    return [
        PaymentResponse(
            id=str(p.id),
            amount=p.amount,
            currency=p.currency,
            status=p.status,
            payment_method=p.payment_method,
            paid_at=p.paid_at.isoformat() if p.paid_at else None,
            created_at=p.created_at.isoformat()
        )
        for p in payments
    ]


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get specific payment.
    Verifies ownership before returning.
    """
    payment = payment_service.get_payment_by_id(payment_id, current_user_id, db)
    
    return PaymentResponse(
        id=str(payment.id),
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        payment_method=payment.payment_method,
        paid_at=payment.paid_at.isoformat() if payment.paid_at else None,
        created_at=payment.created_at.isoformat()
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook handler.
    Processes payment success/failure events.
    """
    import stripe
    import os
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle events
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        payment_service.handle_payment_success(payment_intent["id"], db)
    
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        payment_service.handle_payment_failure(payment_intent["id"], db)
    
    return {"status": "success"}
