"""
Pricing service for cost calculation and provider rate management.
Handles dynamic pricing configuration and real-time cost estimation.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from database.models import PricingConfig


class PricingService:
    """Service for pricing configuration and cost calculation"""
    
    def get_active_pricing(self, service_type: str, provider: str, model: Optional[str] = None, db: Session = None) -> PricingConfig:
        """Get active pricing for a service/provider/model"""
        query = db.query(PricingConfig).filter(
            PricingConfig.service_type == service_type,
            PricingConfig.provider == provider,
            PricingConfig.is_active == True,
            PricingConfig.effective_from <= datetime.utcnow()
        )
        
        if model:
            query = query.filter(PricingConfig.model == model)
        
        # Get most recent effective pricing
        pricing = query.order_by(PricingConfig.effective_from.desc()).first()
        
        if not pricing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active pricing found for {service_type}/{provider}/{model}"
            )
        
        return pricing
    
    def calculate_llm_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        db: Session
    ) -> Decimal:
        """Calculate LLM cost based on tokens"""
        # Get input pricing
        input_pricing = self.get_active_pricing("llm_input", provider, model, db)
        # Get output pricing
        output_pricing = self.get_active_pricing("llm_output", provider, model, db)
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_pricing.cost_per_unit
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_pricing.cost_per_unit
        
        return input_cost + output_cost
    
    def calculate_tts_cost(
        self,
        provider: str,
        model: str,
        characters: int,
        db: Session
    ) -> Decimal:
        """Calculate TTS cost based on characters"""
        pricing = self.get_active_pricing("tts", provider, model, db)
        
        # Calculate cost (pricing is per 1M characters)
        cost = (Decimal(characters) / Decimal(1_000_000)) * pricing.cost_per_unit
        
        return cost
    
    def calculate_stt_cost(
        self,
        provider: str,
        model: str,
        duration_seconds: int,
        db: Session
    ) -> Decimal:
        """Calculate STT cost based on duration"""
        pricing = self.get_active_pricing("stt", provider, model, db)
        
        # Calculate cost (pricing is per minute)
        duration_minutes = Decimal(duration_seconds) / Decimal(60)
        cost = duration_minutes * pricing.cost_per_unit
        
        return cost
    
    def calculate_telephony_cost(
        self,
        provider: str,
        duration_seconds: int,
        db: Session
    ) -> Decimal:
        """Calculate telephony cost based on duration"""
        pricing = self.get_active_pricing("telephony", provider, None, db)
        
        # Calculate cost (pricing is per minute)
        duration_minutes = Decimal(duration_seconds) / Decimal(60)
        cost = duration_minutes * pricing.cost_per_unit
        
        return cost
    
    def calculate_call_cost(
        self,
        llm_provider: str,
        llm_model: str,
        input_tokens: int,
        output_tokens: int,
        tts_provider: str,
        tts_model: str,
        tts_characters: int,
        stt_provider: str,
        stt_model: str,
        stt_duration: int,
        telephony_provider: str,
        call_duration: int,
        platform_fee_percentage: Decimal = Decimal("7.00"),
        db: Session = None
    ) -> Dict[str, Decimal]:
        """
        Calculate complete call cost breakdown.
        Returns dict with all cost components.
        """
        # Calculate individual costs
        llm_cost = self.calculate_llm_cost(llm_provider, llm_model, input_tokens, output_tokens, db)
        tts_cost = self.calculate_tts_cost(tts_provider, tts_model, tts_characters, db)
        stt_cost = self.calculate_stt_cost(stt_provider, stt_model, stt_duration, db)
        telephony_cost = self.calculate_telephony_cost(telephony_provider, call_duration, db)
        
        # Calculate base cost
        base_cost = llm_cost + tts_cost + stt_cost + telephony_cost
        
        # Calculate platform fee
        platform_fee = base_cost * (platform_fee_percentage / Decimal("100"))
        
        # Calculate total cost
        total_cost = base_cost + platform_fee
        
        return {
            "llm_cost": llm_cost,
            "tts_cost": tts_cost,
            "stt_cost": stt_cost,
            "telephony_cost": telephony_cost,
            "base_cost": base_cost,
            "platform_fee": platform_fee,
            "platform_fee_percentage": platform_fee_percentage,
            "total_cost": total_cost
        }
    
    def estimate_call_cost(
        self,
        estimated_duration_seconds: int,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o-mini",
        tts_provider: str = "elevenlabs",
        tts_model: str = "standard",
        stt_provider: str = "deepgram",
        stt_model: str = "nova-2",
        telephony_provider: str = "twilio",
        db: Session = None
    ) -> Dict[str, Decimal]:
        """
        Estimate call cost based on expected duration.
        Uses average token/character usage per minute.
        """
        # Estimate metrics (averages per minute)
        duration_minutes = estimated_duration_seconds / 60
        estimated_input_tokens = int(duration_minutes * 150)  # ~150 input tokens/min
        estimated_output_tokens = int(duration_minutes * 100)  # ~100 output tokens/min
        estimated_characters = int(duration_minutes * 120)  # ~120 chars/min
        
        return self.calculate_call_cost(
            llm_provider=llm_provider,
            llm_model=llm_model,
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            tts_provider=tts_provider,
            tts_model=tts_model,
            tts_characters=estimated_characters,
            stt_provider=stt_provider,
            stt_model=stt_model,
            stt_duration=estimated_duration_seconds,
            telephony_provider=telephony_provider,
            call_duration=estimated_duration_seconds,
            db=db
        )
    
    def seed_default_pricing(self, db: Session):
        """Seed database with default pricing configuration"""
        default_pricing = [
            # LLM Input Pricing (per 1M tokens)
            PricingConfig(
                service_type="llm_input",
                provider="openai",
                model="gpt-4o",
                unit_type="per_1m_tokens",
                cost_per_unit=Decimal("2.50"),
                currency="USD"
            ),
            PricingConfig(
                service_type="llm_input",
                provider="openai",
                model="gpt-4o-mini",
                unit_type="per_1m_tokens",
                cost_per_unit=Decimal("0.15"),
                currency="USD"
            ),
            # LLM Output Pricing (per 1M tokens)
            PricingConfig(
                service_type="llm_output",
                provider="openai",
                model="gpt-4o",
                unit_type="per_1m_tokens",
                cost_per_unit=Decimal("10.00"),
                currency="USD"
            ),
            PricingConfig(
                service_type="llm_output",
                provider="openai",
                model="gpt-4o-mini",
                unit_type="per_1m_tokens",
                cost_per_unit=Decimal("0.60"),
                currency="USD"
            ),
            # TTS Pricing (per 1M characters)
            PricingConfig(
                service_type="tts",
                provider="elevenlabs",
                model="standard",
                unit_type="per_1m_characters",
                cost_per_unit=Decimal("30.00"),
                currency="USD"
            ),
            PricingConfig(
                service_type="tts",
                provider="openai",
                model="standard",
                unit_type="per_1m_characters",
                cost_per_unit=Decimal("15.00"),
                currency="USD"
            ),
            # STT Pricing (per minute)
            PricingConfig(
                service_type="stt",
                provider="deepgram",
                model="nova-2",
                unit_type="per_minute",
                cost_per_unit=Decimal("0.0098"),
                currency="USD"
            ),
            PricingConfig(
                service_type="stt",
                provider="openai",
                model="whisper",
                unit_type="per_minute",
                cost_per_unit=Decimal("0.006"),
                currency="USD"
            ),
            # Telephony Pricing (per minute)
            PricingConfig(
                service_type="telephony",
                provider="twilio",
                model=None,
                unit_type="per_minute",
                cost_per_unit=Decimal("0.0085"),
                currency="USD"
            ),
            PricingConfig(
                service_type="telephony",
                provider="plivo",
                model=None,
                unit_type="per_minute",
                cost_per_unit=Decimal("0.0070"),
                currency="USD"
            ),
        ]
        
        for pricing in default_pricing:
            # Check if already exists
            existing = db.query(PricingConfig).filter(
                PricingConfig.service_type == pricing.service_type,
                PricingConfig.provider == pricing.provider,
                PricingConfig.model == pricing.model
            ).first()
            
            if not existing:
                db.add(pricing)
        
        db.commit()
        print("✅ Default pricing configuration seeded")


# Singleton instance
pricing_service = PricingService()
