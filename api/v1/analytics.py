"""
Analytics API endpoints.
Handles dashboard statistics and usage reports.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta

from database.connection import get_db
from services.auth import get_current_user_id
from services.analytics_service import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


# Response Models
class DashboardStatsResponse(BaseModel):
    total_calls: int
    total_duration: int
    total_spent: float
    avg_duration: float
    calls_this_month: int
    spent_this_month: float
    calls_today: int
    spent_today: float
    active_agents: int


class CostBreakdownResponse(BaseModel):
    llm_cost: float
    tts_cost: float
    stt_cost: float
    telephony_cost: float
    base_cost: float
    platform_fee: float
    total_cost: float


class DailyUsageResponse(BaseModel):
    date: str
    calls: int
    duration: int
    cost: float


class AgentPerformanceResponse(BaseModel):
    agent_id: str
    agent_name: str
    total_calls: int
    total_duration: int
    total_cost: float
    avg_duration: float
    avg_cost: float


# Endpoints
@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for authenticated user.
    User can only access their own stats.
    """
    stats = analytics_service.get_dashboard_stats(current_user_id, db)
    return DashboardStatsResponse(**stats)


@router.get("/cost-breakdown", response_model=CostBreakdownResponse)
def get_cost_breakdown(
    start_date: datetime,
    end_date: datetime,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get cost breakdown by service type for date range.
    User can only access their own data.
    """
    breakdown = analytics_service.get_cost_breakdown(current_user_id, start_date, end_date, db)
    return CostBreakdownResponse(**breakdown)


@router.get("/daily-usage", response_model=List[DailyUsageResponse])
def get_daily_usage(
    days: int = 30,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get daily usage for the last N days.
    User can only access their own data.
    """
    usage = analytics_service.get_daily_usage(current_user_id, days, db)
    return [DailyUsageResponse(**u) for u in usage]


@router.get("/agent-performance", response_model=List[AgentPerformanceResponse])
def get_agent_performance(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for all user's agents.
    User can only access their own agents.
    """
    performance = analytics_service.get_agent_performance(current_user_id, db)
    return [AgentPerformanceResponse(**p) for p in performance]
