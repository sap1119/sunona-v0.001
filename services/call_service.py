"""
Call service for call history and conversation management.
Ensures user can only access their own calls.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException, status
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
import uuid

from database.models import CallHistory, Conversation, Agent
from services.wallet_service import wallet_service
from services.pricing_service import pricing_service


class CallService:
    """Service for call operations with user isolation"""
    
    def create_call(
        self,
        user_id: str,
        agent_id: str,
        phone_number: str,
        direction: str,
        call_sid: Optional[str] = None,
        db: Session = None
    ) -> CallHistory:
        """
        Create new call record.
        Verifies agent ownership.
        """
        # Verify agent belongs to user
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == user_id
        ).first()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or access denied"
            )
        
        call = CallHistory(
            user_id=user_id,
            agent_id=agent_id,
            call_sid=call_sid,
            phone_number=phone_number,
            direction=direction,
            status="initiated",
            started_at=datetime.utcnow()
        )
        
        db.add(call)
        db.commit()
        db.refresh(call)
        
        return call
    
    def end_call_and_calculate_cost(
        self,
        call_id: str,
        user_id: str,
        duration: int,
        llm_tokens_input: int,
        llm_tokens_output: int,
        tts_characters: int,
        agent_config: Dict,
        db: Session = None
    ) -> CallHistory:
        """
        End call, calculate costs, and deduct from wallet.
        CRITICAL: Verifies call ownership before processing.
        """
        # Get call and verify ownership
        call = db.query(CallHistory).filter(
            CallHistory.id == call_id,
            CallHistory.user_id == user_id  # Ownership check
        ).first()
        
        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Call not found"
            )
        
        # Extract provider info from agent config
        llm_provider = agent_config.get("llm_config", {}).get("provider", "openai")
        llm_model = agent_config.get("llm_config", {}).get("model", "gpt-4o-mini")
        tts_provider = agent_config.get("voice_config", {}).get("provider", "elevenlabs")
        tts_model = agent_config.get("voice_config", {}).get("model", "standard")
        stt_provider = agent_config.get("transcriber_config", {}).get("provider", "deepgram")
        stt_model = agent_config.get("transcriber_config", {}).get("model", "nova-2")
        telephony_provider = agent_config.get("telephony_config", {}).get("provider", "twilio")
        
        # Calculate costs
        cost_breakdown = pricing_service.calculate_call_cost(
            llm_provider=llm_provider,
            llm_model=llm_model,
            input_tokens=llm_tokens_input,
            output_tokens=llm_tokens_output,
            tts_provider=tts_provider,
            tts_model=tts_model,
            tts_characters=tts_characters,
            stt_provider=stt_provider,
            stt_model=stt_model,
            stt_duration=duration,
            telephony_provider=telephony_provider,
            call_duration=duration,
            db=db
        )
        
        # Update call record
        call.duration = duration
        call.llm_cost = cost_breakdown["llm_cost"]
        call.tts_cost = cost_breakdown["tts_cost"]
        call.stt_cost = cost_breakdown["stt_cost"]
        call.telephony_cost = cost_breakdown["telephony_cost"]
        call.base_cost = cost_breakdown["base_cost"]
        call.platform_fee = cost_breakdown["platform_fee"]
        call.platform_fee_percentage = cost_breakdown["platform_fee_percentage"]
        call.total_cost = cost_breakdown["total_cost"]
        call.llm_tokens_used = llm_tokens_input + llm_tokens_output
        call.tts_characters_used = tts_characters
        call.stt_duration = duration
        call.status = "completed"
        call.ended_at = datetime.utcnow()
        
        # Deduct cost from wallet
        wallet_service.deduct_funds(
            user_id=user_id,
            amount=cost_breakdown["total_cost"],
            description=f"Call cost - {duration}s",
            reference_id=str(call.id),
            reference_type="call",
            db=db
        )
        
        # Update agent statistics
        agent = db.query(Agent).filter(Agent.id == call.agent_id).first()
        if agent:
            agent.total_calls += 1
            agent.total_duration += duration
            agent.total_cost += cost_breakdown["total_cost"]
        
        db.commit()
        db.refresh(call)
        
        return call
    
    def get_user_calls(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        db: Session = None
    ) -> List[CallHistory]:
        """
        Get user's call history.
        CRITICAL: Only returns calls for the specified user_id.
        """
        query = db.query(CallHistory).filter(CallHistory.user_id == user_id)
        
        if status:
            query = query.filter(CallHistory.status == status)
        
        calls = query.order_by(CallHistory.created_at.desc())\\
            .limit(limit)\\
            .offset(offset)\\
            .all()
        
        return calls
    
    def get_call_by_id(
        self,
        call_id: str,
        user_id: str,
        db: Session
    ) -> CallHistory:
        """
        Get specific call.
        CRITICAL: Verifies ownership before returning.
        """
        call = db.query(CallHistory).filter(
            CallHistory.id == call_id,
            CallHistory.user_id == user_id  # Ownership check
        ).first()
        
        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Call not found"
            )
        
        return call
    
    def get_call_transcript(
        self,
        call_id: str,
        user_id: str,
        db: Session
    ) -> List[Conversation]:
        """
        Get call transcript.
        CRITICAL: Verifies call ownership first.
        """
        # Verify call ownership
        call = self.get_call_by_id(call_id, user_id, db)
        
        # Get conversations
        conversations = db.query(Conversation)\\
            .filter(Conversation.call_id == call.id)\\
            .order_by(Conversation.timestamp)\\
            .all()
        
        return conversations
    
    def add_conversation_message(
        self,
        call_id: str,
        speaker: str,
        message: str,
        message_type: str = "text",
        confidence: Optional[Decimal] = None,
        db: Session = None
    ) -> Conversation:
        """Add message to conversation transcript"""
        conversation = Conversation(
            call_id=call_id,
            speaker=speaker,
            message=message,
            message_type=message_type,
            confidence=confidence
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    def get_user_statistics(
        self,
        user_id: str,
        db: Session
    ) -> Dict:
        """
        Get user's call statistics.
        CRITICAL: Only returns stats for the specified user_id.
        """
        stats = db.query(
            func.count(CallHistory.id).label("total_calls"),
            func.sum(CallHistory.duration).label("total_duration"),
            func.avg(CallHistory.duration).label("avg_duration"),
            func.sum(CallHistory.total_cost).label("total_spent"),
            func.count(func.nullif(CallHistory.status == "completed", False)).label("successful_calls"),
            func.count(func.nullif(CallHistory.status == "failed", False)).label("failed_calls")
        ).filter(CallHistory.user_id == user_id).first()
        
        return {
            "total_calls": stats.total_calls or 0,
            "total_duration": int(stats.total_duration or 0),
            "avg_duration": float(stats.avg_duration or 0),
            "total_spent": float(stats.total_spent or 0),
            "successful_calls": stats.successful_calls or 0,
            "failed_calls": stats.failed_calls or 0
        }


# Singleton instance
call_service = CallService()
