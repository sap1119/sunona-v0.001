import os
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
from pydantic import BaseModel

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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class CreateAgentPayload(BaseModel):
    agent_config: AgentModel
    agent_prompts: Optional[Dict[str, Dict[str, str]]] = None


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
        if not retrieved_agent_config:
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

        agents = [{ "agent_id": key, "data": json.loads(data) } for key, data in zip(agent_keys, agents_data) if data]

        return {"agents": agents}

    except Exception as e:
        logger.error(f"Error fetching all agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


############################################################################################# 
# WebSocket - Simplified Mock Version for Testing
#############################################################################################
@app.websocket("/chat/v1/{agent_id}")
async def websocket_endpoint(agent_id: str, websocket: WebSocket, user_agent: str = Query(None)):
    logger.info(f"WebSocket connection attempt for agent_id: {agent_id}")
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        # Get agent config
        retrieved_agent_config = await redis_client.get(agent_id)
        if not retrieved_agent_config:
            logger.error(f"Agent {agent_id} not found in storage")
            await websocket.send_json({
                "type": "error",
                "message": "Agent not found"
            })
            await websocket.close(code=1008, reason="Agent not found")
            return
            
        logger.info(f"Retrieved agent config for {agent_id}")
        agent_config = json.loads(retrieved_agent_config)
        
        # Send welcome message
        welcome_msg = agent_config.get("agent_welcome_message", "Hello! How can I help you?")
        await websocket.send_json({
            "type": "system",
            "text": f"Connected to agent: {agent_config.get('agent_name', 'Unknown')}"
        })
        
        await websocket.send_json({
            "type": "system",
            "text": welcome_msg
        })
        
        logger.info(f"WebSocket connected successfully for agent {agent_id}")
        
        # Keep connection alive and echo messages
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Received message: {data}")
                
                # Echo back for now
                await websocket.send_json({
                    "type": "response",
                    "text": f"Echo: {data.get('text', 'No text provided')}"
                })
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for agent {agent_id}")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                traceback.print_exc()
                break
                
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent config: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Invalid agent configuration"
        })
        await websocket.close(code=1008, reason="Invalid agent configuration")
    except Exception as e:
        logger.error(f"Error in WebSocket: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Error: {str(e)}"
            })
        except:
            pass
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
