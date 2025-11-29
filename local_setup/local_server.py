import os
import sys
import asyncio
import uuid
import traceback
import json
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sunona.helpers.utils import store_file
from sunona.prompts import *
from sunona.helpers.logger_config import configure_logger
from sunona.models import *
from sunona.llms import LiteLLM
from sunona.agent_manager.assistant_manager import AssistantManager
from pydantic import BaseModel

# Add parent directory to path for database imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database imports
try:
    from database.connection import init_db
    from api.v1 import api_router
    DATABASE_ENABLED = True
except ImportError:
    print("⚠️  Database modules not found. Running without database integration.")
    DATABASE_ENABLED = False

load_dotenv()
logger = configure_logger(__name__)

class MockRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value

    async def delete(self, key):
        if key in self.store:
            del self.store[key]

    async def keys(self, pattern="*"):
        if pattern == "*":
            return list(self.store.keys())
        return []

    async def exists(self, key):
        return key in self.store

redis_client = MockRedis()
active_websockets: List[WebSocket] = []

# Create FastAPI app
app = FastAPI(
    title="Sunona Voice AI Platform",
    description="Pay-as-you-go voice AI platform with complete user data isolation",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include database API routers if available
if DATABASE_ENABLED:
    app.include_router(api_router)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup"""
        try:
            print("🔧 Initializing database...")
            init_db()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"⚠️  Database initialization error: {e}")


class CreateAgentPayload(BaseModel):
    agent_config: AgentModel
    agent_prompts: Optional[Dict[str, Dict[str, str]]] = None


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Sunona Voice AI Platform",
        "version": "2.0.0",
        "database": "connected" if DATABASE_ENABLED else "disabled"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    endpoints = {
        "message": "Sunona Voice AI Platform API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }
    
    if DATABASE_ENABLED:
        endpoints["api"] = {
            "auth": "/api/v1/auth",
            "wallet": "/api/v1/wallet",
            "calls": "/api/v1/calls",
            "agents": "/api/v1/agents",
            "payments": "/api/v1/payments",
            "analytics": "/api/v1/analytics",
            "pricing": "/api/v1/pricing"
        }
    
    return endpoints


# Legacy agent endpoints (MockRedis-based)
@app.get("/agent/{agent_id}")
async def get_agent(agent_id: str):
    """Fetches an agent's information by ID."""
    try:
        agent_data = await redis_client.get(agent_id)
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")
        return json.loads(agent_data)
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/agent")
async def create_agent(agent_data: CreateAgentPayload):
    agent_uuid = str(uuid.uuid4())
    data_for_db = agent_data.agent_config.model_dump()
    data_for_db["assistant_status"] = "seeding"
    agent_prompts = agent_data.agent_prompts
    logger.info(f'Data for DB {data_for_db}')

    if len(data_for_db['tasks']) > 0:
        logger.info("Setting up follow up tasks")
        for index, task in enumerate(data_for_db['tasks']):
            if task['task_type'] == "extraction":
                extraction_prompt_llm = os.getenv("EXTRACTION_PROMPT_GENERATION_MODEL")
                if extraction_prompt_llm:
                    extraction_prompt_generation_llm = LiteLLM(model=extraction_prompt_llm, max_tokens=2000)
                    extraction_prompt = await extraction_prompt_generation_llm.generate(
                        messages=[
                            {'role': 'system', 'content': EXTRACTION_PROMPT_GENERATION_PROMPT},
                            {'role': 'user', 'content': data_for_db["tasks"][index]['tools_config']["llm_agent"]['extraction_details']}
                        ])
                    data_for_db["tasks"][index]["tools_config"]["llm_agent"]['extraction_json'] = extraction_prompt

    stored_prompt_file_path = f"{agent_uuid}/conversation_details.json"
    
    tasks = [redis_client.set(agent_uuid, json.dumps(data_for_db))]
    if agent_prompts:
        tasks.append(store_file(file_key=stored_prompt_file_path, file_data=agent_prompts, local=True))
    
    await asyncio.gather(*tasks)
    return {"agent_id": agent_uuid, "state": "created"}


@app.put("/agent/{agent_id}")
async def edit_agent(agent_id: str, agent_data: CreateAgentPayload = Body(...)):
    """Edits an existing agent based on the provided agent_id."""
    try:
        existing_data = await redis_client.get(agent_id)
        if not existing_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        new_data = agent_data.agent_config.model_dump()
        new_data["assistant_status"] = "updated"
        agent_prompts = agent_data.agent_prompts
        logger.info(f"Updating Agent {agent_id}: {new_data}")

        for index, task in enumerate(new_data.get("tasks", [])):
            if task.get("task_type") == "extraction":
                extraction_prompt_llm = os.getenv("EXTRACTION_PROMPT_GENERATION_MODEL")
                if extraction_prompt_llm:
                    extraction_prompt_generation_llm = LiteLLM(model=extraction_prompt_llm, max_tokens=2000)
                    extraction_details = task["tools_config"]["llm_agent"].get("extraction_details", "")
                    extraction_prompt = await extraction_prompt_generation_llm.generate(
                        messages=[
                            {"role": "system", "content": EXTRACTION_PROMPT_GENERATION_PROMPT},
                            {"role": "user", "content": extraction_details}
                        ]
                    )
                    new_data["tasks"][index]["tools_config"]["llm_agent"]["extraction_json"] = extraction_prompt

        stored_prompt_file_path = f"{agent_id}/conversation_details.json"
        tasks = [redis_client.set(agent_id, json.dumps(new_data))]
        if agent_prompts:
            tasks.append(store_file(file_key=stored_prompt_file_path, file_data=agent_prompts, local=True))
        await asyncio.gather(*tasks)
        return {"agent_id": agent_id, "state": "updated"}
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/agent/{agent_id}")
async def delete_agent(agent_id: str):
    """Deletes an agent by ID."""
    try:
        agent_exists = await redis_client.exists(agent_id)
        if not agent_exists:
            raise HTTPException(status_code=404, detail="Agent not found")
        await redis_client.delete(agent_id)
        return {"agent_id": agent_id, "state": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/all")
async def get_all_agents():
    """Fetches all agents stored in Redis."""
    try:
        agent_keys = await redis_client.keys("*")
        if not agent_keys:
            return {"agents": []}
        agents_data = []
        for key in agent_keys:
            try:
                data = await redis_client.get(key)
                agents_data.append(data)
            except Exception as e:
                logger.error(f"An error occurred with key {key}: {e}")
        agents = [{"agent_id": key, "data": json.loads(data)} for key, data in zip(agent_keys, agents_data) if data]
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Error fetching all agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# WebSocket endpoint
@app.websocket("/chat/v1/{agent_id}")
async def websocket_endpoint(
    agent_id: str, 
    websocket: WebSocket, 
    user_agent: str = Query(None),
    user_id: str = Query(None),  # NEW: For database tracking
    phone_number: str = Query(None),  # NEW: For call records
    call_sid: str = Query(None)  # NEW: For telephony integration
):
    logger.info(f"WebSocket connection attempt for agent_id: {agent_id}, user_id: {user_id}")
    await websocket.accept()
    active_websockets.append(websocket)
    agent_config, context_data = None, None
    
    try:
        retrieved_agent_config = await redis_client.get(agent_id)
        if not retrieved_agent_config:
            logger.error(f"Agent {agent_id} not found in storage")
            await websocket.close(code=1008, reason="Agent not found")
            return
        logger.info(f"Retrieved agent config for {agent_id}")
        agent_config = json.loads(retrieved_agent_config)
        logger.info(f"Agent config structure: {json.dumps(agent_config, indent=2)}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent config: {e}")
        traceback.print_exc()
        await websocket.close(code=1008, reason="Invalid agent configuration")
        return
    except Exception as e:
        logger.error(f"Error retrieving agent config: {e}")
        traceback.print_exc()
        await websocket.close(code=1008, reason="Agent retrieval failed")
        return

    try:
        logger.info(f"Creating AssistantManager for agent {agent_id}")
        assistant_manager = AssistantManager(
            agent_config, 
            websocket, 
            agent_id,
            user_id=user_id,  # NEW: Pass user_id for tracking
            phone_number=phone_number,  # NEW: Pass phone number
            call_sid=call_sid  # NEW: Pass call SID
        )
        logger.info("AssistantManager created successfully")
        logger.info("Starting assistant_manager.run(local=True)")
        async for index, task_output in assistant_manager.run(local=True):
            logger.info(f"Task output {index}: {task_output}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for agent {agent_id}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket execution for agent {agent_id}: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": f"Error: {str(e)}"})
        except:
            pass
        if websocket in active_websockets:
            active_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "local_server:app",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="info"
    )
