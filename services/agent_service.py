"""
Agent service for agent management.
Ensures user can only access their own agents.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Optional, Dict
import uuid

from database.models import Agent


class AgentService:
    """Service for agent operations with user isolation"""
    
    def create_agent(
        self,
        user_id: str,
        name: str,
        agent_type: str,
        description: Optional[str] = None,
        welcome_message: Optional[str] = None,
        system_prompt: Optional[str] = None,
        voice_config: Optional[Dict] = None,
        llm_config: Optional[Dict] = None,
        transcriber_config: Optional[Dict] = None,
        telephony_config: Optional[Dict] = None,
        db: Session = None
    ) -> Agent:
        """Create new agent for user"""
        agent = Agent(
            user_id=user_id,
            name=name,
            type=agent_type,
            description=description,
            welcome_message=welcome_message,
            system_prompt=system_prompt,
            voice_config=voice_config or {},
            llm_config=llm_config or {},
            transcriber_config=transcriber_config or {},
            telephony_config=telephony_config or {},
            is_active=True
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        return agent
    
    def get_user_agents(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        db: Session = None
    ) -> List[Agent]:
        """
        Get user's agents.
        CRITICAL: Only returns agents for the specified user_id.
        """
        query = db.query(Agent).filter(Agent.user_id == user_id)
        
        if is_active is not None:
            query = query.filter(Agent.is_active == is_active)
        
        agents = query.order_by(Agent.created_at.desc()).all()
        
        return agents
    
    def get_agent_by_id(
        self,
        agent_id: str,
        user_id: str,
        db: Session
    ) -> Agent:
        """
        Get specific agent.
        CRITICAL: Verifies ownership before returning.
        """
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == user_id  # Ownership check
        ).first()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        return agent
    
    def update_agent(
        self,
        agent_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        welcome_message: Optional[str] = None,
        system_prompt: Optional[str] = None,
        voice_config: Optional[Dict] = None,
        llm_config: Optional[Dict] = None,
        transcriber_config: Optional[Dict] = None,
        telephony_config: Optional[Dict] = None,
        is_active: Optional[bool] = None,
        db: Session = None
    ) -> Agent:
        """
        Update agent.
        CRITICAL: Verifies ownership before updating.
        """
        agent = self.get_agent_by_id(agent_id, user_id, db)
        
        # Update fields if provided
        if name is not None:
            agent.name = name
        if description is not None:
            agent.description = description
        if welcome_message is not None:
            agent.welcome_message = welcome_message
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if voice_config is not None:
            agent.voice_config = voice_config
        if llm_config is not None:
            agent.llm_config = llm_config
        if transcriber_config is not None:
            agent.transcriber_config = transcriber_config
        if telephony_config is not None:
            agent.telephony_config = telephony_config
        if is_active is not None:
            agent.is_active = is_active
        
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        
        return agent
    
    def delete_agent(
        self,
        agent_id: str,
        user_id: str,
        db: Session
    ) -> bool:
        """
        Delete agent.
        CRITICAL: Verifies ownership before deleting.
        """
        agent = self.get_agent_by_id(agent_id, user_id, db)
        
        db.delete(agent)
        db.commit()
        
        return True
    
    def get_agent_statistics(
        self,
        agent_id: str,
        user_id: str,
        db: Session
    ) -> Dict:
        """
        Get agent statistics.
        CRITICAL: Verifies ownership first.
        """
        agent = self.get_agent_by_id(agent_id, user_id, db)
        
        return {
            "total_calls": agent.total_calls,
            "total_duration": agent.total_duration,
            "total_cost": float(agent.total_cost),
            "avg_duration": agent.total_duration / agent.total_calls if agent.total_calls > 0 else 0
        }


# Singleton instance
agent_service = AgentService()
