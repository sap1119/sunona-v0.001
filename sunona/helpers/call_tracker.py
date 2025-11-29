"""
Database tracker for Sunona Voice AI Engine.
Automatically tracks costs, usage, and stores call data during voice calls.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database.connection import SessionLocal
    from database.models import CallHistory, Conversation
    from services.pricing_service import pricing_service
    from services.call_service import call_service
    from services.wallet_service import wallet_service
    DATABASE_ENABLED = True
except ImportError:
    DATABASE_ENABLED = False
    print("⚠️  Database modules not available. Call tracking disabled.")


class CallTracker:
    """Tracks call metrics and costs during voice AI calls"""
    
    def __init__(self, user_id: str, agent_id: str, phone_number: str = None, direction: str = "outbound"):
        self.user_id = user_id
        self.agent_id = agent_id
        self.phone_number = phone_number
        self.direction = direction
        self.call_id = None
        self.start_time = None
        self.end_time = None
        
        # Usage metrics
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
        self.tts_characters = 0
        self.stt_duration = 0
        
        # Provider info
        self.llm_provider = "openai"
        self.llm_model = "gpt-4o-mini"
        self.tts_provider = "elevenlabs"
        self.tts_model = "standard"
        self.stt_provider = "deepgram"
        self.stt_model = "nova-2"
        self.telephony_provider = "twilio"
        
        self.db = None
        if DATABASE_ENABLED:
            self.db = SessionLocal()
    
    def set_providers(self, agent_config: Dict):
        """Extract provider info from agent config"""
        try:
            # Extract from first task's tools_config
            if agent_config.get('tasks'):
                tools_config = agent_config['tasks'][0].get('tools_config', {})
                
                # LLM config
                llm_agent = tools_config.get('llm_agent', {})
                if isinstance(llm_agent, dict):
                    llm_config = llm_agent.get('llm_config', llm_agent)
                    self.llm_provider = llm_config.get('provider', 'openai')
                    self.llm_model = llm_config.get('model', 'gpt-4o-mini')
                
                # TTS config
                synthesizer = tools_config.get('synthesizer', {})
                if isinstance(synthesizer, dict):
                    self.tts_provider = synthesizer.get('provider', 'elevenlabs')
                    self.tts_model = synthesizer.get('provider_config', {}).get('model', 'standard')
                
                # STT config
                transcriber = tools_config.get('transcriber', {})
                if isinstance(transcriber, dict):
                    self.stt_provider = transcriber.get('provider', 'deepgram')
                    self.stt_model = transcriber.get('model', 'nova-2')
                
                # Telephony config
                output_config = tools_config.get('output', {})
                if isinstance(output_config, dict):
                    self.telephony_provider = output_config.get('provider', 'twilio')
        except Exception as e:
            print(f"⚠️  Error extracting provider info: {e}")
    
    async def start_call(self, call_sid: str = None):
        """Start tracking a call"""
        self.start_time = datetime.utcnow()
        
        if DATABASE_ENABLED and self.db:
            try:
                call = call_service.create_call(
                    user_id=self.user_id,
                    agent_id=self.agent_id,
                    phone_number=self.phone_number or "unknown",
                    direction=self.direction,
                    call_sid=call_sid,
                    db=self.db
                )
                self.call_id = str(call.id)
                print(f"✅ Call tracking started: {self.call_id}")
            except Exception as e:
                print(f"⚠️  Error starting call tracking: {e}")
    
    def track_llm_usage(self, input_tokens: int, output_tokens: int):
        """Track LLM token usage"""
        self.llm_input_tokens += input_tokens
        self.llm_output_tokens += output_tokens
    
    def track_tts_usage(self, characters: int):
        """Track TTS character usage"""
        self.tts_characters += characters
    
    def track_stt_usage(self, duration_seconds: int):
        """Track STT duration"""
        self.stt_duration += duration_seconds
    
    async def add_conversation_message(self, speaker: str, message: str, message_type: str = "text"):
        """Add message to conversation transcript"""
        if DATABASE_ENABLED and self.db and self.call_id:
            try:
                call_service.add_conversation_message(
                    call_id=self.call_id,
                    speaker=speaker,
                    message=message,
                    message_type=message_type,
                    db=self.db
                )
            except Exception as e:
                print(f"⚠️  Error adding conversation message: {e}")
    
    async def end_call(self, agent_config: Dict):
        """End call and calculate costs"""
        self.end_time = datetime.utcnow()
        duration = int((self.end_time - self.start_time).total_seconds())
        
        if DATABASE_ENABLED and self.db and self.call_id:
            try:
                # End call and calculate costs
                call = call_service.end_call_and_calculate_cost(
                    call_id=self.call_id,
                    user_id=self.user_id,
                    duration=duration,
                    llm_tokens_input=self.llm_input_tokens,
                    llm_tokens_output=self.llm_output_tokens,
                    tts_characters=self.tts_characters,
                    agent_config=agent_config,
                    db=self.db
                )
                
                print(f"✅ Call ended. Cost: ${call.total_cost}")
                print(f"   - LLM: ${call.llm_cost}")
                print(f"   - TTS: ${call.tts_cost}")
                print(f"   - STT: ${call.stt_cost}")
                print(f"   - Telephony: ${call.telephony_cost}")
                print(f"   - Platform Fee (7%): ${call.platform_fee}")
                
                return {
                    "call_id": self.call_id,
                    "duration": duration,
                    "total_cost": float(call.total_cost),
                    "breakdown": {
                        "llm_cost": float(call.llm_cost),
                        "tts_cost": float(call.tts_cost),
                        "stt_cost": float(call.stt_cost),
                        "telephony_cost": float(call.telephony_cost),
                        "platform_fee": float(call.platform_fee)
                    }
                }
            except Exception as e:
                print(f"⚠️  Error ending call tracking: {e}")
                return None
        
        return None
    
    def __del__(self):
        """Cleanup database session"""
        if self.db:
            self.db.close()


# Singleton for easy access
_current_tracker: Optional[CallTracker] = None


def get_current_tracker() -> Optional[CallTracker]:
    """Get the current call tracker"""
    return _current_tracker


def set_current_tracker(tracker: CallTracker):
    """Set the current call tracker"""
    global _current_tracker
    _current_tracker = tracker


def clear_current_tracker():
    """Clear the current call tracker"""
    global _current_tracker
    _current_tracker = None
