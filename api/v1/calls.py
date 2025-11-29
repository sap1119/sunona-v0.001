"""
Call API endpoints.
Handles call history, transcripts, and statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from database.connection import get_db
from services.auth import get_current_user_id
from services.call_service import call_service

router = APIRouter(prefix="/api/v1/calls", tags=["Calls"])


# Response Models
class CallResponse(BaseModel):
    id: str
    agent_id: str
    phone_number: str
    direction: str
    status: str
    duration: Optional[int]
    llm_cost: Decimal
    tts_cost: Decimal
    stt_cost: Decimal
    telephony_cost: Decimal
    base_cost: Decimal
    platform_fee: Decimal
    total_cost: Decimal
    started_at: Optional[str]
    ended_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    speaker: str
    message: str
    message_type: str
    timestamp: str

    class Config:
        from_attributes = True


class CallStatisticsResponse(BaseModel):
    total_calls: int
    total_duration: int
    avg_duration: float
    total_spent: float
    successful_calls: int
    failed_calls: int


# Endpoints
@router.get("/", response_model=List[CallResponse])
def get_my_calls(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's call history.
    User can only access their own calls.
    """
    calls = call_service.get_user_calls(current_user_id, limit, offset, status, db)
    
    return [
        CallResponse(
            id=str(c.id),
            agent_id=str(c.agent_id),
            phone_number=c.phone_number,
            direction=c.direction,
            status=c.status,
            duration=c.duration,
            llm_cost=c.llm_cost,
            tts_cost=c.tts_cost,
            stt_cost=c.stt_cost,
            telephony_cost=c.telephony_cost,
            base_cost=c.base_cost,
            platform_fee=c.platform_fee,
            total_cost=c.total_cost,
            started_at=c.started_at.isoformat() if c.started_at else None,
            ended_at=c.ended_at.isoformat() if c.ended_at else None,
            created_at=c.created_at.isoformat()
        )
        for c in calls
    ]


@router.get("/{call_id}", response_model=CallResponse)
def get_call(
    call_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get specific call details.
    Verifies ownership before returning.
    """
    call = call_service.get_call_by_id(call_id, current_user_id, db)
    
    return CallResponse(
        id=str(call.id),
        agent_id=str(call.agent_id),
        phone_number=call.phone_number,
        direction=call.direction,
        status=call.status,
        duration=call.duration,
        llm_cost=call.llm_cost,
        tts_cost=call.tts_cost,
        stt_cost=call.stt_cost,
        telephony_cost=call.telephony_cost,
        base_cost=call.base_cost,
        platform_fee=call.platform_fee,
        total_cost=call.total_cost,
        started_at=call.started_at.isoformat() if call.started_at else None,
        ended_at=call.ended_at.isoformat() if call.ended_at else None,
        created_at=call.created_at.isoformat()
    )


@router.get("/{call_id}/transcript", response_model=List[ConversationResponse])
def get_call_transcript(
    call_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get call transcript.
    Verifies call ownership before returning.
    """
    conversations = call_service.get_call_transcript(call_id, current_user_id, db)
    
    return [
        ConversationResponse(
            id=str(c.id),
            speaker=c.speaker,
            message=c.message,
            message_type=c.message_type,
            timestamp=c.timestamp.isoformat()
        )
        for c in conversations
    ]


@router.get("/statistics/me", response_model=CallStatisticsResponse)
def get_my_statistics(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get authenticated user's call statistics"""
    stats = call_service.get_user_statistics(current_user_id, db)
    return CallStatisticsResponse(**stats)
