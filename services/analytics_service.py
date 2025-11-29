"""
Analytics service for usage reports and statistics.
Ensures user can only access their own analytics.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
import calendar

from database.models import CallHistory, UsageAnalytics, Agent


class AnalyticsService:
    """Service for analytics and reporting"""
    
    def get_dashboard_stats(
        self,
        user_id: str,
        db: Session
    ) -> Dict:
        """
        Get dashboard statistics for user.
        CRITICAL: Only returns stats for the specified user_id.
        """
        # Overall stats
        overall = db.query(
            func.count(CallHistory.id).label("total_calls"),
            func.sum(CallHistory.duration).label("total_duration"),
            func.sum(CallHistory.total_cost).label("total_spent"),
            func.avg(CallHistory.duration).label("avg_duration")
        ).filter(CallHistory.user_id == user_id).first()
        
        # This month stats
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_stats = db.query(
            func.count(CallHistory.id).label("calls_this_month"),
            func.sum(CallHistory.total_cost).label("spent_this_month")
        ).filter(
            CallHistory.user_id == user_id,
            CallHistory.created_at >= month_start
        ).first()
        
        # Today stats
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_stats = db.query(
            func.count(CallHistory.id).label("calls_today"),
            func.sum(CallHistory.total_cost).label("spent_today")
        ).filter(
            CallHistory.user_id == user_id,
            CallHistory.created_at >= today_start
        ).first()
        
        # Active agents count
        active_agents = db.query(func.count(Agent.id)).filter(
            Agent.user_id == user_id,
            Agent.is_active == True
        ).scalar()
        
        return {
            "total_calls": overall.total_calls or 0,
            "total_duration": int(overall.total_duration or 0),
            "total_spent": float(overall.total_spent or 0),
            "avg_duration": float(overall.avg_duration or 0),
            "calls_this_month": month_stats.calls_this_month or 0,
            "spent_this_month": float(month_stats.spent_this_month or 0),
            "calls_today": today_stats.calls_today or 0,
            "spent_today": float(today_stats.spent_today or 0),
            "active_agents": active_agents or 0
        }
    
    def get_cost_breakdown(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict:
        """
        Get cost breakdown by service type.
        CRITICAL: Only returns data for the specified user_id.
        """
        breakdown = db.query(
            func.sum(CallHistory.llm_cost).label("llm_cost"),
            func.sum(CallHistory.tts_cost).label("tts_cost"),
            func.sum(CallHistory.stt_cost).label("stt_cost"),
            func.sum(CallHistory.telephony_cost).label("telephony_cost"),
            func.sum(CallHistory.base_cost).label("base_cost"),
            func.sum(CallHistory.platform_fee).label("platform_fee"),
            func.sum(CallHistory.total_cost).label("total_cost")
        ).filter(
            CallHistory.user_id == user_id,
            CallHistory.created_at >= start_date,
            CallHistory.created_at <= end_date
        ).first()
        
        return {
            "llm_cost": float(breakdown.llm_cost or 0),
            "tts_cost": float(breakdown.tts_cost or 0),
            "stt_cost": float(breakdown.stt_cost or 0),
            "telephony_cost": float(breakdown.telephony_cost or 0),
            "base_cost": float(breakdown.base_cost or 0),
            "platform_fee": float(breakdown.platform_fee or 0),
            "total_cost": float(breakdown.total_cost or 0)
        }
    
    def get_daily_usage(
        self,
        user_id: str,
        days: int = 30,
        db: Session
    ) -> List[Dict]:
        """
        Get daily usage for the last N days.
        CRITICAL: Only returns data for the specified user_id.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        daily_data = db.query(
            func.date(CallHistory.created_at).label("date"),
            func.count(CallHistory.id).label("calls"),
            func.sum(CallHistory.duration).label("duration"),
            func.sum(CallHistory.total_cost).label("cost")
        ).filter(
            CallHistory.user_id == user_id,
            CallHistory.created_at >= start_date
        ).group_by(func.date(CallHistory.created_at))\\
         .order_by(func.date(CallHistory.created_at))\\
         .all()
        
        return [
            {
                "date": str(row.date),
                "calls": row.calls,
                "duration": int(row.duration or 0),
                "cost": float(row.cost or 0)
            }
            for row in daily_data
        ]
    
    def get_agent_performance(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict]:
        """
        Get performance metrics for all user's agents.
        CRITICAL: Only returns data for the specified user_id.
        """
        agents = db.query(Agent).filter(Agent.user_id == user_id).all()
        
        performance = []
        for agent in agents:
            performance.append({
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "total_calls": agent.total_calls,
                "total_duration": agent.total_duration,
                "total_cost": float(agent.total_cost),
                "avg_duration": agent.total_duration / agent.total_calls if agent.total_calls > 0 else 0,
                "avg_cost": float(agent.total_cost) / agent.total_calls if agent.total_calls > 0 else 0
            })
        
        return performance
    
    def update_monthly_analytics(
        self,
        user_id: str,
        year: int,
        month: int,
        db: Session
    ) -> UsageAnalytics:
        """
        Update or create monthly analytics record.
        Called periodically to aggregate data.
        """
        # Get month boundaries
        month_start = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        month_end = datetime(year, month, last_day, 23, 59, 59)
        
        # Check if record exists
        analytics = db.query(UsageAnalytics).filter(
            UsageAnalytics.user_id == user_id,
            UsageAnalytics.period_start == month_start
        ).first()
        
        if not analytics:
            analytics = UsageAnalytics(
                user_id=user_id,
                period_start=month_start,
                period_end=month_end
            )
            db.add(analytics)
        
        # Aggregate data from calls
        stats = db.query(
            func.count(CallHistory.id).label("total_calls"),
            func.sum(CallHistory.duration).label("total_duration"),
            func.count(func.nullif(CallHistory.status == "completed", False)).label("successful"),
            func.count(func.nullif(CallHistory.status == "failed", False)).label("failed"),
            func.sum(CallHistory.llm_cost).label("llm_cost"),
            func.sum(CallHistory.tts_cost).label("tts_cost"),
            func.sum(CallHistory.stt_cost).label("stt_cost"),
            func.sum(CallHistory.telephony_cost).label("telephony_cost"),
            func.sum(CallHistory.total_cost).label("total_cost"),
            func.sum(CallHistory.llm_tokens_used).label("tokens"),
            func.sum(CallHistory.tts_characters_used).label("characters"),
            func.sum(CallHistory.stt_duration).label("stt_duration")
        ).filter(
            CallHistory.user_id == user_id,
            CallHistory.created_at >= month_start,
            CallHistory.created_at <= month_end
        ).first()
        
        # Update analytics
        analytics.total_calls = stats.total_calls or 0
        analytics.total_duration = stats.total_duration or 0
        analytics.successful_calls = stats.successful or 0
        analytics.failed_calls = stats.failed or 0
        analytics.llm_cost = stats.llm_cost or Decimal("0.0000")
        analytics.tts_cost = stats.tts_cost or Decimal("0.0000")
        analytics.stt_cost = stats.stt_cost or Decimal("0.0000")
        analytics.telephony_cost = stats.telephony_cost or Decimal("0.0000")
        analytics.total_cost = stats.total_cost or Decimal("0.0000")
        analytics.llm_tokens_used = stats.tokens or 0
        analytics.tts_characters_used = stats.characters or 0
        analytics.stt_duration = stats.stt_duration or 0
        analytics.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(analytics)
        
        return analytics


# Singleton instance
analytics_service = AnalyticsService()
