"""
Pricing API endpoints.
Handles pricing information and cost estimation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

from database.connection import get_db
from services.auth import get_current_user_id
from services.pricing_service import pricing_service

router = APIRouter(prefix="/api/v1/pricing", tags=["Pricing"])


# Request/Response Models
class EstimateRequest(BaseModel):
    estimated_duration_seconds: int
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    tts_provider: str = "elevenlabs"
    tts_model: str = "standard"
    stt_provider: str = "deepgram"
    stt_model: str = "nova-2"
    telephony_provider: str = "twilio"


class CostEstimateResponse(BaseModel):
    llm_cost: Decimal
    tts_cost: Decimal
    stt_cost: Decimal
    telephony_cost: Decimal
    base_cost: Decimal
    platform_fee: Decimal
    platform_fee_percentage: Decimal
    total_cost: Decimal


# Endpoints
@router.post("/estimate", response_model=CostEstimateResponse)
def estimate_call_cost(
    request: EstimateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Estimate call cost based on expected duration.
    Uses average token/character usage per minute.
    """
    estimate = pricing_service.estimate_call_cost(
        estimated_duration_seconds=request.estimated_duration_seconds,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        tts_provider=request.tts_provider,
        tts_model=request.tts_model,
        stt_provider=request.stt_provider,
        stt_model=request.stt_model,
        telephony_provider=request.telephony_provider,
        db=db
    )
    
    return CostEstimateResponse(**estimate)


@router.get("/current")
def get_current_pricing(db: Session = Depends(get_db)):
    """
    Get current pricing configuration.
    Public endpoint (no auth required).
    """
    return {
        "llm": {
            "gpt-4o": {
                "input": 2.50,
                "output": 10.00,
                "unit": "per_1m_tokens"
            },
            "gpt-4o-mini": {
                "input": 0.15,
                "output": 0.60,
                "unit": "per_1m_tokens"
            }
        },
        "tts": {
            "elevenlabs": {
                "standard": 30.00,
                "turbo": 120.00,
                "unit": "per_1m_characters"
            },
            "openai": {
                "standard": 15.00,
                "hd": 30.00,
                "unit": "per_1m_characters"
            }
        },
        "stt": {
            "deepgram": {
                "rate": 0.0098,
                "unit": "per_minute"
            },
            "whisper": {
                "rate": 0.006,
                "unit": "per_minute"
            }
        },
        "telephony": {
            "twilio": {
                "rate": 0.0085,
                "unit": "per_minute"
            },
            "plivo": {
                "rate": 0.0070,
                "unit": "per_minute"
            }
        },
        "platform_fee": {
            "percentage": 7,
            "description": "Platform maintenance and support"
        }
    }
