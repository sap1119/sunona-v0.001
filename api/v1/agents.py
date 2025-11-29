"""
Agent API endpoints.
Handles agent CRUD operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

from database.connection import get_db
from services.auth import get_current_user_id
from services.agent_service import agent_service

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


# Request/Response Models
class CreateAgentRequest(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    welcome_message: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_config: Optional[Dict] = None
    llm_config: Optional[Dict] = None
    transcriber_config: Optional[Dict] = None
    telephony_config: Optional[Dict] = None


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    welcome_message: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_config: Optional[Dict] = None
    llm_config: Optional[Dict] = None
    transcriber_config: Optional[Dict] = None
    telephony_config: Optional[Dict] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str]
    welcome_message: Optional[str]
    system_prompt: Optional[str]
    voice_config: Dict
    llm_config: Dict
    transcriber_config: Dict
    telephony_config: Dict
    is_active: bool
    total_calls: int
    total_duration: int
    total_cost: float
    created_at: str

    class Config:
        from_attributes = True


class AgentStatisticsResponse(BaseModel):
    total_calls: int
    total_duration: int
    total_cost: float
    avg_duration: float


# Endpoints
@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    request: CreateAgentRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create new agent for authenticated user"""
    agent = agent_service.create_agent(
        user_id=current_user_id,
        name=request.name,
        agent_type=request.type,
        description=request.description,
        welcome_message=request.welcome_message,
        system_prompt=request.system_prompt,
        voice_config=request.voice_config,
        llm_config=request.llm_config,
        transcriber_config=request.transcriber_config,
        telephony_config=request.telephony_config,
        db=db
    )
    
    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        type=agent.type,
        description=agent.description,
        welcome_message=agent.welcome_message,
        system_prompt=agent.system_prompt,
        voice_config=agent.voice_config,
        llm_config=agent.llm_config,
        transcriber_config=agent.transcriber_config,
        telephony_config=agent.telephony_config,
        is_active=agent.is_active,
        total_calls=agent.total_calls,
        total_duration=agent.total_duration,
        total_cost=float(agent.total_cost),
        created_at=agent.created_at.isoformat()
    )


@router.get("/", response_model=List[AgentResponse])
def get_my_agents(
    is_active: Optional[bool] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's agents.
    User can only access their own agents.
    """
    agents = agent_service.get_user_agents(current_user_id, is_active, db)
    
    return [
        AgentResponse(
            id=str(a.id),
            name=a.name,
            type=a.type,
            description=a.description,
            welcome_message=a.welcome_message,
            system_prompt=a.system_prompt,
            voice_config=a.voice_config,
            llm_config=a.llm_config,
            transcriber_config=a.transcriber_config,
            telephony_config=a.telephony_config,
            is_active=a.is_active,
            total_calls=a.total_calls,
            total_duration=a.total_duration,
            total_cost=float(a.total_cost),
            created_at=a.created_at.isoformat()
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get specific agent.
    Verifies ownership before returning.
    """
    agent = agent_service.get_agent_by_id(agent_id, current_user_id, db)
    
    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        type=agent.type,
        description=agent.description,
        welcome_message=agent.welcome_message,
        system_prompt=agent.system_prompt,
        voice_config=agent.voice_config,
        llm_config=agent.llm_config,
        transcriber_config=agent.transcriber_config,
        telephony_config=agent.telephony_config,
        is_active=agent.is_active,
        total_calls=agent.total_calls,
        total_duration=agent.total_duration,
        total_cost=float(agent.total_cost),
        created_at=agent.created_at.isoformat()
    )


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update agent.
    Verifies ownership before updating.
    """
    agent = agent_service.update_agent(
        agent_id=agent_id,
        user_id=current_user_id,
        name=request.name,
        description=request.description,
        welcome_message=request.welcome_message,
        system_prompt=request.system_prompt,
        voice_config=request.voice_config,
        llm_config=request.llm_config,
        transcriber_config=request.transcriber_config,
        telephony_config=request.telephony_config,
        is_active=request.is_active,
        db=db
    )
    
    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        type=agent.type,
        description=agent.description,
        welcome_message=agent.welcome_message,
        system_prompt=agent.system_prompt,
        voice_config=agent.voice_config,
        llm_config=agent.llm_config,
        transcriber_config=agent.transcriber_config,
        telephony_config=agent.telephony_config,
        is_active=agent.is_active,
        total_calls=agent.total_calls,
        total_duration=agent.total_duration,
        total_cost=float(agent.total_cost),
        created_at=agent.created_at.isoformat()
    )


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete agent.
    Verifies ownership before deleting.
    """
    agent_service.delete_agent(agent_id, current_user_id, db)
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/statistics", response_model=AgentStatisticsResponse)
def get_agent_statistics(
    agent_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get agent statistics.
    Verifies ownership before returning.
    """
    stats = agent_service.get_agent_statistics(agent_id, current_user_id, db)
    return AgentStatisticsResponse(**stats)
