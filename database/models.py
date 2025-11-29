"""
SQLAlchemy ORM models for Sunona platform.
Defines all database tables and relationships.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, DECIMAL, Text,
    ForeignKey, UniqueConstraint, CheckConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .connection import Base


class User(Base):
    """User accounts and authentication"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    company_name = Column(String(255))
    phone = Column(String(50))
    avatar_url = Column(Text)
    role = Column(String(50), default='user')  # user, admin
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    agents = relationship("Agent", back_populates="user")
    calls = relationship("CallHistory", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class Wallet(Base):
    """User wallet for top-up and balance management"""
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    balance = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    currency = Column(String(3), default='USD')
    total_topped_up = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    total_spent = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    low_balance_threshold = Column(DECIMAL(10, 4), default=Decimal('10.0000'))
    auto_recharge_enabled = Column(Boolean, default=False)
    auto_recharge_amount = Column(DECIMAL(10, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet")
    topup_payments = relationship("TopUpPayment", back_populates="wallet")

    def __repr__(self):
        return f"<Wallet user_id={self.user_id} balance={self.balance}>"


class WalletTransaction(Base):
    """Wallet transaction history"""
    __tablename__ = "wallet_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(50), nullable=False)  # topup, deduction, refund, bonus
    amount = Column(DECIMAL(10, 4), nullable=False)
    balance_before = Column(DECIMAL(10, 4), nullable=False)
    balance_after = Column(DECIMAL(10, 4), nullable=False)
    description = Column(Text)
    reference_id = Column(UUID(as_uuid=True))  # Links to payment or call
    reference_type = Column(String(50))  # payment, call, refund
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")

    def __repr__(self):
        return f"<WalletTransaction {self.type} {self.amount}>"


class Agent(Base):
    """AI voice agents"""
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50))  # sales, support, conversational
    description = Column(Text)
    welcome_message = Column(Text)
    system_prompt = Column(Text)
    voice_config = Column(JSONB)  # {provider: 'elevenlabs', voice: 'George', ...}
    llm_config = Column(JSONB)  # {provider: 'openai', model: 'gpt-4', ...}
    transcriber_config = Column(JSONB)  # {provider: 'deepgram', model: 'nova-2', ...}
    telephony_config = Column(JSONB)  # {provider: 'twilio', ...}
    is_active = Column(Boolean, default=True)
    total_calls = Column(Integer, default=0)
    total_duration = Column(Integer, default=0)  # seconds
    total_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="agents")
    calls = relationship("CallHistory", back_populates="agent")

    def __repr__(self):
        return f"<Agent {self.name}>"


class CallHistory(Base):
    """Call history with detailed cost breakdown"""
    __tablename__ = "call_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='SET NULL'))
    call_sid = Column(String(255))  # Twilio/Plivo call ID
    phone_number = Column(String(50))
    direction = Column(String(20))  # inbound, outbound
    status = Column(String(50))  # initiated, ringing, in-progress, completed, failed
    duration = Column(Integer)  # seconds

    # Cost Breakdown
    llm_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    tts_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    stt_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    telephony_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    base_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    platform_fee = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    platform_fee_percentage = Column(DECIMAL(5, 2), default=Decimal('7.00'))
    total_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))

    # Usage Metrics
    llm_tokens_used = Column(Integer)
    tts_characters_used = Column(Integer)
    stt_duration = Column(Integer)  # seconds

    recording_url = Column(Text)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="calls")
    agent = relationship("Agent", back_populates="calls")
    conversations = relationship("Conversation", back_populates="call")

    def __repr__(self):
        return f"<CallHistory {self.call_sid} ${self.total_cost}>"


class Conversation(Base):
    """Conversation transcripts"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey('call_history.id', ondelete='CASCADE'), nullable=False)
    speaker = Column(String(50))  # user, agent, system
    message = Column(Text, nullable=False)
    message_type = Column(String(50))  # text, audio, system
    confidence = Column(DECIMAL(5, 4))
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSONB)

    # Relationships
    call = relationship("CallHistory", back_populates="conversations")

    def __repr__(self):
        return f"<Conversation {self.speaker}: {self.message[:50]}>"


class TopUpPayment(Base):
    """Top-up payment records"""
    __tablename__ = "topup_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default='USD')
    status = Column(String(50))  # pending, succeeded, failed, refunded
    payment_method = Column(String(50))  # card, bank_transfer, paypal
    stripe_payment_intent_id = Column(String(255))
    stripe_charge_id = Column(String(255))
    description = Column(Text)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    wallet = relationship("Wallet", back_populates="topup_payments")

    def __repr__(self):
        return f"<TopUpPayment ${self.amount} {self.status}>"


class PricingConfig(Base):
    """Pricing configuration for different providers"""
    __tablename__ = "pricing_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_type = Column(String(50), nullable=False)  # llm, tts, stt, telephony
    provider = Column(String(100), nullable=False)  # openai, elevenlabs, deepgram, twilio
    model = Column(String(100))  # gpt-4, nova-2, etc.
    unit_type = Column(String(50))  # per_minute, per_token, per_character
    cost_per_unit = Column(DECIMAL(10, 6), nullable=False)
    currency = Column(String(3), default='USD')
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_until = Column(DateTime)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('service_type', 'provider', 'model', 'effective_from', name='uq_pricing_config'),
    )

    def __repr__(self):
        return f"<PricingConfig {self.service_type}/{self.provider}>"


class UsageAnalytics(Base):
    """Usage analytics per user per period"""
    __tablename__ = "usage_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Call Metrics
    total_calls = Column(Integer, default=0)
    total_duration = Column(Integer, default=0)  # seconds
    successful_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)

    # Cost Breakdown
    llm_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    tts_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    stt_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    telephony_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))
    total_cost = Column(DECIMAL(10, 4), default=Decimal('0.0000'))

    # Usage Metrics
    llm_tokens_used = Column(Integer, default=0)
    tts_characters_used = Column(Integer, default=0)
    stt_duration = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'period_start', name='uq_user_period'),
    )

    def __repr__(self):
        return f"<UsageAnalytics user_id={self.user_id} calls={self.total_calls}>"


class APIKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(20))  # First 8 chars for display
    name = Column(String(100))
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... {self.name}>"
